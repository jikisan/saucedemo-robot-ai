*** Settings ***
Documentation       Element actions addressed by locator key (``page.element`` in ``locators/locators.yaml``).
...                 Every page object goes through these keywords, so locator resolution has one
...                 choke point. Each action waits explicitly before acting.
...                 Templated locators accept named arguments, e.g. ``product=Sauce Labs Backpack``.
...
...                 Actions resolve keys through ``Resolve Locator`` (self-healing). Count and
...                 "is gone" checks use the plain primary locator: absence is a valid answer there.
Library             SeleniumLibrary
Library             Collections
Library             libraries.utils.data_loader
Library             libraries.ai_assist.self_healing.SelfHealing


*** Variables ***
${RETRY_INTERVAL}     200ms


*** Keywords ***
Click Locator
    [Arguments]    ${key}    &{params}
    ${locator}=    Resolve Locator    ${key}    &{params}
    Wait Until Element Is Visible    ${locator}
    Retry On Stale Element    Click Element    ${locator}

Input Into Locator
    [Arguments]    ${key}    ${text}    &{params}
    ${locator}=    Resolve Locator    ${key}    &{params}
    Wait Until Element Is Visible    ${locator}
    Retry On Stale Element    Input Text    ${locator}    ${text}

Input Secret Into Locator
    [Documentation]    Like ``Input Into Locator`` but keeps the value out of the log.
    [Arguments]    ${key}    ${secret}
    ${locator}=    Resolve Locator    ${key}
    Wait Until Element Is Visible    ${locator}
    Retry On Stale Element    Input Password    ${locator}    ${secret}

Select Value From Locator
    [Arguments]    ${key}    ${value}
    ${locator}=    Resolve Locator    ${key}
    Wait Until Element Is Visible    ${locator}
    Retry On Stale Element    Select From List By Value    ${locator}    ${value}

Get Text Of Locator
    [Arguments]    ${key}    &{params}
    ${locator}=    Resolve Locator    ${key}    &{params}
    Wait Until Element Is Visible    ${locator}
    ${text}=    Retry On Stale Element    Get Text    ${locator}
    RETURN    ${text}

Get Texts Of Locator
    [Documentation]    Returns the visible text of every element matching the key.
    [Arguments]    ${key}
    ${locator}=    Resolve Locator    ${key}
    Wait Until Element Is Visible    ${locator}
    ${texts}=    Retry On Stale Element    Read Texts Of Elements    ${locator}
    RETURN    ${texts}

Read Texts Of Elements
    [Arguments]    ${locator}
    ${elements}=    Get WebElements    ${locator}
    ${texts}=    Create List
    FOR    ${element}    IN    @{elements}
        ${text}=    Get Text    ${element}
        Append To List    ${texts}    ${text}
    END
    RETURN    ${texts}

Get Count Of Locator
    [Arguments]    ${key}
    ${locator}=    Get Locator    ${key}
    ${count}=    Get Element Count    ${locator}
    RETURN    ${count}

Wait Until Locator Is Visible
    [Arguments]    ${key}    ${timeout}=${None}    &{params}
    ${locator}=    Resolve Locator    ${key}    timeout=${timeout}    &{params}
    Wait Until Element Is Visible    ${locator}    ${timeout}

Wait Until Locator Is Gone
    [Arguments]    ${key}    &{params}
    ${locator}=    Get Locator    ${key}    &{params}
    Wait Until Page Does Not Contain Element    ${locator}

Retry On Stale Element
    [Documentation]    Runs a SeleniumLibrary keyword, retrying within the Selenium timeout if it fails,
    ...                e.g. because the element went stale during a re-render. Safe for these actions:
    ...                a stale click never happened, and ``Input Text`` clears the field first.
    [Arguments]    ${keyword}    @{args}
    ${timeout}=    Get Selenium Timeout
    ${result}=    Wait Until Keyword Succeeds    ${timeout}    ${RETRY_INTERVAL}    ${keyword}    @{args}
    RETURN    ${result}
