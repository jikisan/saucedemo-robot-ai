*** Settings ***
Documentation       Header shared by all logged-in pages: title, cart icon/badge and side menu.
Resource            ../elements.resource


*** Keywords ***
Open Cart
    [Documentation]    Opens the cart through the header cart icon.
    Click Locator    header.cart_link

Logout
    [Documentation]    Logs out through the side menu.
    Click Locator    header.menu_button
    Click Locator    header.logout_link

Page Title Should Be
    [Documentation]    Verifies the page title in the header equals ``expected``.
    [Arguments]    ${expected}
    ${title}=    Get Text Of Locator    header.title
    Should Be Equal    ${title}    ${expected}

Cart Badge Should Show
    [Documentation]    Verifies the cart badge shows ``expected_count`` items.
    [Arguments]    ${expected_count}
    ${count}=    Get Text Of Locator    header.cart_badge
    Should Be Equal As Integers    ${count}    ${expected_count}

Cart Badge Should Not Be Visible
    [Documentation]    Verifies the cart badge is hidden, meaning the cart is empty.
    Wait Until Locator Is Gone    header.cart_badge
