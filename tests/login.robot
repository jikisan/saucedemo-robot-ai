*** Settings ***
Documentation       Authentication: valid login, rejected credentials, logout and access control.
Resource            ../resources/common.resource
Resource            ../resources/pages/LoginPage.resource
Resource            ../resources/pages/InventoryPage.resource
Suite Setup         Open Application Browser
Suite Teardown      Close Application Browser
Test Setup          Reset Application State


*** Variables ***
${GLITCH_LOGIN_TIMEOUT}     20s


*** Test Cases ***
Standard User Can Log In
    [Tags]    smoke    regression
    Login As And Open Inventory    standard

Locked Out User Is Rejected
    [Tags]    negative    regression
    Login As    locked_out
    Login Error Should Contain    Sorry, this user has been locked out.
    Login Page Should Be Open

Wrong Password Is Rejected
    [Tags]    negative
    [Template]    Credentials Should Be Rejected
    standard_user    wrong_password    Username and password do not match any user in this service

Missing Username Is Rejected
    [Tags]    negative
    [Template]    Credentials Should Be Rejected
    ${EMPTY}    secret_sauce    Username is required

Missing Password Is Rejected
    [Tags]    negative
    [Template]    Credentials Should Be Rejected
    standard_user    ${EMPTY}    Password is required

User Can Log Out
    [Tags]    regression
    Login As And Open Inventory    standard
    Logout
    Login Page Should Be Open

Inventory Requires Login
    [Tags]    negative    edge
    Go To    ${BASE_URL}/inventory.html
    Login Error Should Contain    You can only access '/inventory.html' when you are logged in.

Performance Glitch User Logs In Within Extended Timeout
    [Documentation]    Login is deliberately slow for this user; it must still finish within ${GLITCH_LOGIN_TIMEOUT}.
    [Tags]    edge
    Login As And Open Inventory    performance_glitch    timeout=${GLITCH_LOGIN_TIMEOUT}

Self-Healing Recovers An Outdated Login Button Locator
    [Documentation]    The primary locator is wrong on purpose. The run must still log in, warn,
    ...                tag the test ``healed`` and record the fix in ``healing_report.json``.
    [Tags]    ai    edge
    [Setup]    Run Keywords    Reset Application State    AND    Set Selenium Timeout    2s
    [Teardown]    Set Selenium Timeout    ${TIMEOUT}
    Login As Using Outdated Submit Locator    standard
    Inventory Page Should Be Open
    Locator Should Have Been Healed    demo.renamed_login_button


*** Keywords ***
Credentials Should Be Rejected
    [Arguments]    ${username}    ${password}    ${expected_error}
    Submit Credentials    ${username}    ${password}
    Login Error Should Contain    ${expected_error}
    Login Page Should Be Open
