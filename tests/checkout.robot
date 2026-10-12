*** Settings ***
Documentation       Data-driven checkout. One test per row of ``data/checkout.csv``:
...                 an empty ``expected_error`` means the order must complete with correct totals.
Library             DataDriver    file=${CURDIR}/../data/checkout.csv    dialect=excel    encoding=utf-8
Resource            ../resources/common.resource
Resource            ../resources/pages/LoginPage.resource
Resource            ../resources/pages/InventoryPage.resource
Resource            ../resources/pages/CartPage.resource
Resource            ../resources/pages/CheckoutPage.resource
Suite Setup         Open Application Browser
Suite Teardown      Close Application Browser
Test Setup          Reset Application State
Test Template       Checkout Should Behave As Expected


*** Variables ***
@{PRODUCTS}         Sauce Labs Backpack    Sauce Labs Bike Light


*** Test Cases ***
Checkout As ${user} With ${first_name} ${last_name} ${postal_code}    standard    Ada    Lovelace    10115    ${EMPTY}


*** Keywords ***
Checkout Should Behave As Expected
    [Arguments]    ${user}    ${first_name}    ${last_name}    ${postal_code}    ${expected_error}
    Login As And Open Inventory    ${user}
    Add Products To Cart    @{PRODUCTS}
    Open Cart
    Proceed To Checkout
    Fill Checkout Information    ${first_name}    ${last_name}    ${postal_code}
    IF    $expected_error
        Checkout Error Should Be    ${expected_error}
    ELSE
        Checkout Overview Should Be Open
        Order Totals Should Add Up
        Finish Order
        Order Should Be Complete
    END
