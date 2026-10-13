*** Settings ***
Documentation       Inventory (Products) page: product list, sorting and add/remove buttons.
Resource            ../elements.resource
Resource            HeaderComponent.resource
Library             String
Library             libraries.ai_assist.visual_validator.VisualValidator


*** Variables ***
&{SORT_OPTIONS}     name ascending=az    name descending=za    price ascending=lohi    price descending=hilo
${EXPECTED_LOOK}    Products page with six distinct product photos in a two-column grid, each with a name,
...                 a price and an aligned "Add to cart" button; cart icon in the top-right header.


*** Keywords ***
Add Products To Cart
    [Documentation]    Clicks "Add to cart" for each product name in ``products``.
    [Arguments]    @{products}
    FOR    ${product}    IN    @{products}
        Click Locator    inventory.add_to_cart    product=${product}
    END

Add Every Product To Cart
    [Documentation]    Adds every product shown on the inventory page to the cart.
    ${names}=    Get Product Names
    Add Products To Cart    @{names}

Remove Product From Inventory
    [Documentation]    Clicks "Remove" for ``product`` on the inventory page.
    [Arguments]    ${product}
    Click Locator    inventory.remove    product=${product}

Sort Products By
    [Documentation]    ``order`` is one of: name ascending, name descending, price ascending, price descending.
    [Arguments]    ${order}
    Select Value From Locator    inventory.sort_select    ${SORT_OPTIONS}[${order}]

Get Product Names
    [Documentation]    Returns the displayed product names, in page order.
    ${names}=    Get Texts Of Locator    inventory.item_name
    RETURN    ${names}

Get Product Prices
    [Documentation]    Returns the displayed product prices as numbers, in page order.
    ${texts}=    Get Texts Of Locator    inventory.item_price
    ${prices}=    Evaluate    [float(text.lstrip('$')) for text in $texts]
    RETURN    ${prices}

Inventory Page Should Be Open
    [Documentation]    Verifies the inventory page is displayed. ``timeout`` overrides the default wait.
    [Arguments]    ${timeout}=${None}
    Wait Until Locator Is Visible    inventory.container    ${timeout}
    Page Title Should Be    Products

Product Count Should Be
    [Documentation]    Verifies the inventory shows ``expected`` products.
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
    [Documentation]    Verifies the button for ``product`` has switched to "Remove".
    [Arguments]    ${product}
    Wait Until Locator Is Visible    inventory.remove    product=${product}

Product Images Should Be Valid
    [Documentation]    Fails on broken, placeholder, duplicated or oddly sized product images.
    Wait Until Locator Is Visible    inventory.item_image
    ${locator}=    Get Locator    inventory.item_image
    Images Should Be Valid    ${locator}

Product Cards Should Be Aligned
    [Documentation]    Fails if any product card button leaves the grid columns or changes size.
    Wait Until Locator Is Visible    inventory.item_button
    ${locator}=    Get Locator    inventory.item_button
    Elements Should Be Aligned    ${locator}

Inventory Should Look Correct To AI Reviewer
    [Documentation]    Advisory vision check; logs findings, never fails.
    Screen Should Match Description    ${EXPECTED_LOOK}
