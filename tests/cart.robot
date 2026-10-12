*** Settings ***
Documentation       Cart contents, removal, navigation and persistence.
Resource            ../resources/common.resource
Resource            ../resources/pages/LoginPage.resource
Resource            ../resources/pages/InventoryPage.resource
Resource            ../resources/pages/CartPage.resource
Suite Setup         Open Application Browser
Suite Teardown      Close Application Browser
Test Setup          Reset Application State


*** Variables ***
${BACKPACK}         Sauce Labs Backpack
${BIKE_LIGHT}       Sauce Labs Bike Light


*** Test Cases ***
Added Products Appear In The Cart
    [Tags]    smoke    regression
    Login As And Open Inventory    standard
    Add Products To Cart    ${BACKPACK}    ${BIKE_LIGHT}
    Open Cart
    Cart Page Should Be Open
    Cart Should Contain Exactly    ${BACKPACK}    ${BIKE_LIGHT}
    Cart Badge Should Show    2

Removing A Product Updates The Cart
    [Tags]    regression
    Login As And Open Inventory    standard
    Add Products To Cart    ${BACKPACK}    ${BIKE_LIGHT}
    Open Cart
    Remove Product From Cart    ${BACKPACK}
    Cart Should Contain Exactly    ${BIKE_LIGHT}
    Cart Badge Should Show    1

Removing The Last Product Empties The Cart
    [Tags]    edge
    Login As And Open Inventory    standard
    Add Products To Cart    ${BACKPACK}
    Open Cart
    Remove Product From Cart    ${BACKPACK}
    Cart Should Be Empty
    Cart Badge Should Not Be Visible

Continue Shopping Returns To Inventory
    [Tags]    regression
    Login As And Open Inventory    standard
    Open Cart
    Continue Shopping
    Inventory Page Should Be Open

Cart Survives A Page Reload
    [Tags]    edge
    Login As And Open Inventory    standard
    Add Products To Cart    ${BACKPACK}
    Open Cart
    Reload Page
    Cart Should Contain Exactly    ${BACKPACK}
