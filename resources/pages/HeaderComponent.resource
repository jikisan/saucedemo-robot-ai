*** Settings ***
Documentation       Header shared by all logged-in pages: title, cart icon/badge and side menu.
Resource            ../elements.resource


*** Keywords ***
Open Cart
    Click Locator    header.cart_link

Logout
    Click Locator    header.menu_button
    Click Locator    header.logout_link

Page Title Should Be
    [Arguments]    ${expected}
    ${title}=    Get Text Of Locator    header.title
    Should Be Equal    ${title}    ${expected}

Cart Badge Should Show
    [Arguments]    ${expected_count}
    ${count}=    Get Text Of Locator    header.cart_badge
    Should Be Equal As Integers    ${count}    ${expected_count}

Cart Badge Should Not Be Visible
    Wait Until Locator Is Gone    header.cart_badge
