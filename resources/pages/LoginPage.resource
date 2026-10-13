*** Settings ***
Documentation       Login page: credentials form and its error banner.
Resource            ../elements.resource
Resource            InventoryPage.resource


*** Keywords ***
Submit Credentials
    [Documentation]    Enters ``username`` and ``password`` and submits the login form. The password is not logged.
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

Login As Using Outdated Submit Locator
    [Documentation]    Self-healing demo: submits through ``demo.renamed_login_button``, whose
    ...                primary locator no longer exists on the page.
    [Arguments]    ${user_key}
    ${user}=    Get User    ${user_key}
    Input Into Locator    login.username    ${user}[username]
    Input Secret Into Locator    login.password    ${user}[password]
    Click Locator    demo.renamed_login_button

Login Page Should Be Open
    [Documentation]    Verifies the login form is displayed.
    Wait Until Locator Is Visible    login.submit

Login Error Should Contain
    [Documentation]    Verifies the login error message contains ``expected``.
    [Arguments]    ${expected}
    ${message}=    Get Text Of Locator    login.error
    Should Contain    ${message}    ${expected}
