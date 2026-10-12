*** Settings ***
Documentation       Product list: content, sorting and add/remove from the inventory page.
Resource            ../resources/common.resource
Resource            ../resources/pages/LoginPage.resource
Resource            ../resources/pages/InventoryPage.resource
Suite Setup         Open Application Browser
Suite Teardown      Close Application Browser
Test Setup          Reset Application State


*** Test Cases ***
Inventory Lists All Six Products
    [Tags]    smoke    regression
    Login As And Open Inventory    standard
    Product Count Should Be    6

Products Sort By Price Low To High
    [Tags]    regression
    [Template]    Sorting Should Work For User
    standard    price ascending

Products Sort By Price High To Low
    [Tags]    regression
    [Template]    Sorting Should Work For User
    standard    price descending

Products Sort By Name Z To A
    [Tags]    regression
    [Template]    Sorting Should Work For User
    standard    name descending

Adding A Product Updates The Cart Badge
    [Tags]    smoke    regression
    Login As And Open Inventory    standard
    Add Products To Cart    Sauce Labs Backpack
    Product Button Should Say Remove    Sauce Labs Backpack
    Cart Badge Should Show    1

Removing A Product Clears The Cart Badge
    [Tags]    regression
    Login As And Open Inventory    standard
    Add Products To Cart    Sauce Labs Backpack
    Remove Product From Inventory    Sauce Labs Backpack
    Cart Badge Should Not Be Visible

Standard User Can Add Every Product
    [Tags]    edge
    [Template]    Every Product Should Be Addable For User
    standard

Problem User Can Sort Products
    [Tags]    known-bug
    [Template]    Sorting Should Work For User
    problem    price ascending

Problem User Can Add Every Product
    [Tags]    known-bug
    [Template]    Every Product Should Be Addable For User
    problem

Error User Can Add Every Product
    [Tags]    known-bug
    [Template]    Every Product Should Be Addable For User
    error


*** Keywords ***
Sorting Should Work For User
    [Arguments]    ${user_key}    ${order}
    Login As And Open Inventory    ${user_key}
    Sort Products By    ${order}
    Products Should Be Sorted By    ${order}

Every Product Should Be Addable For User
    [Arguments]    ${user_key}
    Login As And Open Inventory    ${user_key}
    Add Every Product To Cart
    Cart Badge Should Show    6
