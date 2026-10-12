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


*** Keywords ***
Click Locator
    [Arguments]    ${key}    &{params}
    ${locator}=    Resolve Locator    ${key}    &{params}
    Wait Until Element Is Visible    ${locator}
    Click Element    ${locator}

Input Into Locator
    [Arguments]    ${key}    ${text}    &{params}
    ${locator}=    Resolve Locator    ${key}    &{params}
    Wait Until Element Is Visible    ${locator}
    Input Text    ${locator}    ${text}

Input Secret Into Locator
    [Documentation]    Like ``Input Into Locator`` but keeps the value out of the log.
    [Arguments]    ${key}    ${secret}
    ${locator}=    Resolve Locator    ${key}
    Wait Until Element Is Visible    ${locator}
    Input Password    ${locator}    ${secret}

Select Value From Locator
    [Arguments]    ${key}    ${value}
    ${locator}=    Resolve Locator    ${key}
    Wait Until Element Is Visible    ${locator}
    Select From List By Value    ${locator}    ${value}

Get Text Of Locator
    [Arguments]    ${key}    &{params}
    ${locator}=    Resolve Locator    ${key}    &{params}
    Wait Until Element Is Visible    ${locator}
    ${text}=    Get Text    ${locator}
    RETURN    ${text}

Get Texts Of Locator
    [Documentation]    Returns the visible text of every element matching the key.
    [Arguments]    ${key}
    ${locator}=    Resolve Locator    ${key}
    Wait Until Element Is Visible    ${locator}
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
