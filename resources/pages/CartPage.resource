*** Settings ***
Documentation       Cart page: line items, remove, continue shopping and checkout.
Resource            ../elements.resource
Resource            HeaderComponent.resource


*** Keywords ***
Remove Product From Cart
    [Documentation]    Removes ``product`` from the cart and waits until its row is gone.
    [Arguments]    ${product}
    Click Locator    cart.remove    product=${product}
    Wait Until Locator Is Gone    cart.remove    product=${product}

Continue Shopping
    [Documentation]    Returns from the cart to the inventory page.
    Click Locator    cart.continue_shopping

Proceed To Checkout
    [Documentation]    Starts checkout from the cart page.
    Click Locator    cart.checkout_button

Cart Page Should Be Open
    [Documentation]    Verifies the cart page is displayed.
    Wait Until Locator Is Visible    cart.checkout_button
    Page Title Should Be    Your Cart

Cart Should Contain Exactly
    [Documentation]    Verifies the cart holds exactly ``expected_products``, in any order.
    [Arguments]    @{expected_products}
    ${names}=    Get Texts Of Locator    cart.item_name
    Lists Should Be Equal    ${names}    ${expected_products}    ignore_order=True

Cart Should Be Empty
    [Documentation]    Verifies the cart has no line items.
    ${count}=    Get Count Of Locator    cart.item
    Should Be Equal As Integers    ${count}    0
