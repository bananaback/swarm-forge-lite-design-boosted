Feature: crapper

  Background:
    Given no harness environment overrides

  Scenario: crapper 1 - a covered function carries its complexity, coverage, and CRAP score
    Given a project with a covered function of complexity 1
    When the crap tool runs with existing coverage and all rows
    Then the report lists the function at complexity 1, coverage 100.0%, and CRAP 1.0

  Scenario: crapper 2 - a function absent from the coverage report scores no coverage
    Given a project with a function of complexity 4 absent from the coverage report
    When the crap tool runs with existing coverage
    Then the report lists the function at coverage 0.0% and CRAP 20.0

  Scenario: crapper 3 - the default returns only the rows above CRAP 10
    Given a project with a covered function and an uncovered function of complexity 4
    When the crap tool runs with existing coverage
    Then the report counts 1 row above CRAP 10 and returns only that row

  Scenario: crapper 4 - the report keeps every row when all rows are asked
    Given a project with a covered function and an uncovered function of complexity 4
    When the crap tool runs with existing coverage and all rows
    Then the report returns every function

  Scenario: crapper 5 - a filter keeps only the matching namespace
    Given a project with an uncovered function in alpha.py and an uncovered function in beta.py
    When the crap tool runs with existing coverage and the filter "alpha"
    Then the report lists only the alpha function

  Scenario: crapper 6 - the run writes the crap.edn snapshot
    Given a project with a covered function of complexity 1
    When the crap tool runs with existing coverage
    Then the artifacts hold a crap.edn snapshot naming the function

  Scenario: crapper 7 - the pack reports its CRAP 10 threshold
    Given a project with a covered function of complexity 1
    When the crap tool runs with existing coverage
    Then the report states the CRAP threshold 10
