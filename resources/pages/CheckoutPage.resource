*** Settings ***
Documentation       Checkout flow: information form (step one), overview (step two) and completion.
Resource            ../elements.resource
Resource            HeaderComponent.resource


*** Keywords ***
Fill Checkout Information
    [Arguments]    ${first_name}    ${last_name}    ${postal_code}
    Input Into Locator    checkout.first_name    ${first_name}
    Input Into Locator    checkout.last_name    ${last_name}
    Input Into Locator    checkout.postal_code    ${postal_code}
    Click Locator    checkout.continue_button

Finish Order
    Click Locator    checkout.finish_button

Get Amount Of
    [Documentation]    Reads a money label such as ``Item total: $39.98`` and returns the number.
    [Arguments]    ${key}
    ${text}=    Get Text Of Locator    ${key}
    ${amount}=    Convert To Number    ${text.split('$')[-1]}
    RETURN    ${amount}

Checkout Error Should Be
    [Arguments]    ${expected}
    ${message}=    Get Text Of Locator    checkout.error
    Should Be Equal    ${message}    ${expected}

Checkout Overview Should Be Open
    Wait Until Locator Is Visible    checkout.finish_button
    Page Title Should Be    Checkout: Overview

Order Totals Should Add Up
    [Documentation]    Subtotal equals the sum of line items, and total equals subtotal plus tax.
    ${texts}=    Get Texts Of Locator    checkout.item_price
    ${items_sum}=    Evaluate    sum(float(text.lstrip('$')) for text in $texts)
    ${subtotal}=    Get Amount Of    checkout.subtotal
    ${tax}=    Get Amount Of    checkout.tax
    ${total}=    Get Amount Of    checkout.total
    Should Be Equal As Numbers    ${subtotal}    ${items_sum}    precision=2
    Should Be Equal As Numbers    ${total}    ${subtotal + ${tax}}    precision=2

Order Should Be Complete
    ${header}=    Get Text Of Locator    checkout.complete_header
    Should Be Equal    ${header}    Thank you for your order!
    Page Title Should Be    Checkout: Complete!
