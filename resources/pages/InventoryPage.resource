*** Settings ***
Documentation       Inventory (Products) page: product list, sorting and add/remove buttons.
Resource            ../elements.resource
Resource            HeaderComponent.resource
Library             String


*** Variables ***
&{SORT_OPTIONS}     name ascending=az    name descending=za    price ascending=lohi    price descending=hilo


*** Keywords ***
Add Products To Cart
    [Arguments]    @{products}
    FOR    ${product}    IN    @{products}
        Click Locator    inventory.add_to_cart    product=${product}
    END

Add Every Product To Cart
    ${names}=    Get Product Names
    Add Products To Cart    @{names}

Remove Product From Inventory
    [Arguments]    ${product}
    Click Locator    inventory.remove    product=${product}

Sort Products By
    [Documentation]    ``order`` is one of: name ascending, name descending, price ascending, price descending.
    [Arguments]    ${order}
    Select Value From Locator    inventory.sort_select    ${SORT_OPTIONS}[${order}]

Get Product Names
    ${names}=    Get Texts Of Locator    inventory.item_name
    RETURN    ${names}

Get Product Prices
    ${texts}=    Get Texts Of Locator    inventory.item_price
    ${prices}=    Evaluate    [float(text.lstrip('$')) for text in $texts]
    RETURN    ${prices}

Inventory Page Should Be Open
    [Arguments]    ${timeout}=${None}
    Wait Until Locator Is Visible    inventory.container    ${timeout}
    Page Title Should Be    Products

Product Count Should Be
    [Arguments]    ${expected}
    ${count}=    Get Count Of Locator    inventory.item
    Should Be Equal As Integers    ${count}    ${expected}

Products Should Be Sorted By
    [Documentation]    Verifies the displayed order. Same ``order`` values as ``Sort Products By``.
    [Arguments]    ${order}
    ${field}    ${direction}=    Split String    ${order}
    IF    '${field}' == 'price'
        ${values}=    Get Product Prices
    ELSE
        ${values}=    Get Product Names
    END
    ${expected}=    Evaluate    sorted($values, reverse=$direction == 'descending')
    Lists Should Be Equal    ${values}    ${expected}

Product Button Should Say Remove
    [Arguments]    ${product}
    Wait Until Locator Is Visible    inventory.remove    product=${product}
