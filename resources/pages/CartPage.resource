*** Settings ***
Documentation       Cart page: line items, remove, continue shopping and checkout.
Resource            ../elements.resource
Resource            HeaderComponent.resource


*** Keywords ***
Remove Product From Cart
    [Arguments]    ${product}
    Click Locator    cart.remove    product=${product}
    Wait Until Locator Is Gone    cart.remove    product=${product}

Continue Shopping
    Click Locator    cart.continue_shopping

Proceed To Checkout
    Click Locator    cart.checkout_button

Cart Page Should Be Open
    Wait Until Locator Is Visible    cart.checkout_button
    Page Title Should Be    Your Cart

Cart Should Contain Exactly
    [Arguments]    @{expected_products}
    ${names}=    Get Texts Of Locator    cart.item_name
    Lists Should Be Equal    ${names}    ${expected_products}    ignore_order=True

Cart Should Be Empty
    ${count}=    Get Count Of Locator    cart.item
    Should Be Equal As Integers    ${count}    0
