*** Settings ***
Documentation       Suite and test lifecycle: browser open/close and per-test state reset.
...                 All settings come from ``.env`` via ``libraries/utils/config.py``.
Library             SeleniumLibrary
Variables           libraries.utils.config


*** Variables ***
${WINDOW_WIDTH}         1440
${WINDOW_HEIGHT}        900
# Chrome flags "secret_sauce" as a breached password after the first login and its
# "Change your password" bubble steals keyboard focus, so later typing is lost.
${CHROME_OPTIONS}       add_experimental_option("prefs", {"credentials_enable_service": False, "profile.password_manager_enabled": False, "profile.password_manager_leak_detection": False})


*** Keywords ***
Open Application Browser
    [Documentation]    Suite setup. Opens ``${BROWSER}`` (headless when ``${HEADLESS}``) at ``${BASE_URL}``.
    ${browser}=    Set Variable If    ${HEADLESS}    headless${BROWSER}    ${BROWSER}
    ${options}=    Set Variable If    'chrome' in '${BROWSER}'    ${CHROME_OPTIONS}    ${None}
    Open Browser    ${BASE_URL}    ${browser}    options=${options}
    Set Window Size    ${WINDOW_WIDTH}    ${WINDOW_HEIGHT}
    Set Selenium Timeout    ${TIMEOUT}

Reset Application State
    [Documentation]    Test setup. Clears cookies and storage (session + cart), then opens the login page.
    Delete All Cookies
    Execute Javascript    window.localStorage.clear(); window.sessionStorage.clear();
    Go To    ${BASE_URL}

Close Application Browser
    [Documentation]    Suite teardown.
    Close All Browsers
