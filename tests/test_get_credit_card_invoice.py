from unittest.mock import call

import pytest
import responses

from pyitau.main import ROUTER_URL
from pyitau.pages import AuthenticatedHomePage, CardDetails, Menu2Page


@pytest.fixture
def response_checking_card_menu():
    return """
    <script>
        $(".accordion-box-cartoes").itauAccordion();
        function carregarBoxCartoes() {
            if($(".btnExibirBoxCartoes").hasClass("ajaxRuned")){
                return;
            }

            BoxHelper.renderConteudoBox({
                urlBox : 'PYITAU_CONTEUDO_BOX_CARTOES_OP',
                seletorContainer : ".conteudoBoxCartoes",
                onComplete : function() {
                    $(".btnExibirBoxCartoes").addClass("ajaxRuned");
                }
            });
        }



        function enviarTagueamentoExibirCartoes(){
            adobeDataLayer.pushCustom('itemClicado', 'BTN:PF:Exibir_cartoes');
            adobeDataLayer.pushCustom('events', ['ClickElement']);
            adobeDataLayer.pushRule('customLink');
            adobeDataLayer.sendDataLayer();
        }
    </script>
    """


@pytest.fixture
def authenticated_home_page(response_authenticated_home):
    return AuthenticatedHomePage(response_authenticated_home)


@pytest.fixture
def menu2_page(response_menu2):
    return Menu2Page(response_menu2)


@pytest.fixture
def card_details_page(response_card_details):
    return CardDetails(response_card_details)


@responses.activate
def test_get_credit_card_invoice(
    itau,
    mocker,
    authenticated_home_page,
    menu2_page,
    card_details_page,
    response_card_details,
    response_menu,
    response_menu2,
):
    itau._home = authenticated_home_page
    itau._flow_id = "PYITAU_FLOW_ID"
    itau._client_id = "PYITAU_CLIENT_ID"

    responses.add(
        responses.POST,
        ROUTER_URL,
        body=response_menu,
        match=[
            responses.matchers.header_matcher(
                {"op": authenticated_home_page.op, "segmento": "VAREJO"}
            )
        ],
    )

    responses.add(
        responses.POST,
        ROUTER_URL,
        body=response_menu2,
        match=[responses.matchers.header_matcher({"op": authenticated_home_page.menu_op})],
    )

    responses.add(
        responses.POST,
        ROUTER_URL,
        body=response_card_details,
        match=[
            responses.matchers.header_matcher({
                "op": menu2_page.checking_cards_op,
                "X-FLOW-ID": itau._flow_id,
                "X-CLIENT-ID": itau._client_id,
                "X-Requested-With": "XMLHttpRequest",
            })
        ],
    )

    responses.add(
        responses.POST,
        ROUTER_URL,
        json={"object": {"data": [{"id": "PYITAU_CARD_ID"}]}},
        match=[
            responses.matchers.header_matcher({"op": card_details_page.invoice_op}),
            responses.matchers.urlencoded_params_matcher(
                {"secao": "Cartoes", "item": "Home"}
            ),
        ],
    )

    responses.add(
        responses.POST,
        ROUTER_URL,
        body='',
        match=[
            responses.matchers.header_matcher({"op": card_details_page.invoice_op}),
            responses.matchers.urlencoded_params_matcher(
                {"secao": "Cartoes:MinhaFatura", "item": ""}
            ),
        ]
    )

    responses.add(
        responses.POST,
        ROUTER_URL,
        json={"success": True},
    )

    post_spy = mocker.spy(itau._session, "post")
    assert itau.get_credit_card_invoice() == {"success": True}

    calls = [
        call(
            ROUTER_URL, headers={"op": authenticated_home_page.op, "segmento": "VAREJO"}
        ),
        call(ROUTER_URL, headers={"op": authenticated_home_page.menu_op}),
        call(ROUTER_URL, headers={
            "op": menu2_page.checking_cards_op,
            "X-FLOW-ID": itau._flow_id,
            "X-CLIENT-ID": itau._client_id,
            "X-Requested-With": "XMLHttpRequest",
        }),
        call(
            ROUTER_URL,
            headers={"op": card_details_page.invoice_op},
            data={"secao": "Cartoes", "item": "Home"},
        ),
        call(
            ROUTER_URL,
            headers={"op": card_details_page.invoice_op},
            data={"secao": "Cartoes:MinhaFatura", "item": ""},
        ),
        call(
            ROUTER_URL,
            headers={"op": card_details_page.full_statement_op},
            data='PYITAU_CARD_ID',
        ),
    ]
    post_spy.assert_has_calls(calls)
