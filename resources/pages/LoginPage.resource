*** Settings ***
Documentation       Login page: credentials form and its error banner.
Resource            ../elements.resource
Resource            InventoryPage.resource


*** Keywords ***
Submit Credentials
    [Arguments]    ${username}    ${password}
    Input Into Locator    login.username    ${username}
    Input Secret Into Locator    login.password    ${password}
    Click Locator    login.submit

Login As
    [Documentation]    Logs in as a user key from ``data/users.yaml`` (e.g. ``standard``).
    [Arguments]    ${user_key}
    ${user}=    Get User    ${user_key}
    Submit Credentials    ${user}[username]    ${user}[password]

Login As And Open Inventory
    [Documentation]    Logs in and waits for the inventory page. ``timeout`` overrides the default wait.
    [Arguments]    ${user_key}    ${timeout}=${None}
    Login As    ${user_key}
    Inventory Page Should Be Open    ${timeout}

Login Page Should Be Open
    Wait Until Locator Is Visible    login.submit

Login Error Should Contain
    [Arguments]    ${expected}
    ${message}=    Get Text Of Locator    login.error
    Should Contain    ${message}    ${expected}
