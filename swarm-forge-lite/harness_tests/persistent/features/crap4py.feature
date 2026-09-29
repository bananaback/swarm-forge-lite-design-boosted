Feature: crap4py

  Background:
    Given no harness environment overrides

  Scenario: crap4py 1 - the report lists each function with its coverage and CRAP score
    Given a project with a function of complexity 1 whose lines are all covered
    When the crap4py command runs with existing coverage
    Then the crap4py command succeeds with a report listing the function with complexity 1, coverage 100.0%, and CRAP 1.0

  Scenario: crap4py 2 - a function absent from the coverage file reports unmeasured
    Given a project with a function whose lines are absent from the coverage file
    When the crap4py command runs with existing coverage
    Then the crap4py command succeeds with a report listing the function with coverage unmeasured and CRAP unmeasured

  Scenario: crap4py 3 - a partly covered function reports its coverage fraction
    Given a project with a function of complexity 3 with 1 of its 3 lines hit
    When the crap4py command runs with existing coverage
    Then the crap4py command succeeds with a report listing the function with coverage 33.3% and CRAP 5.7

  Scenario: crap4py 4 - a function above CRAP 10 is counted
    Given a project with a function of complexity 4 whose lines are recorded with zero hits
    When the crap4py command runs with existing coverage
    Then the crap4py command succeeds with a report counting 1 function above CRAP 10

  Scenario: crap4py 5 - a function at CRAP 10 is not counted
    Given a project with a function of complexity 10 whose lines are all covered
    When the crap4py command runs with existing coverage
    Then the crap4py command succeeds with a report listing the function at CRAP 10.0 and counting 0 functions above CRAP 10

  Scenario: crap4py 6 - the report ranks functions worst-first
    Given a project with a covered function and an uncovered function both present in the coverage file
    When the crap4py command runs with existing coverage
    Then the crap4py command succeeds with a report listing the uncovered function before the covered function

  Scenario: crap4py 7 - a filter keeps only matching functions
    Given a project with a function in alpha.py and a function in beta.py
    When the crap4py command runs with existing coverage and the filter "alpha"
    Then the crap4py command succeeds with a report listing only the alpha.py function

  Scenario: crap4py 8 - a missing coverage file is refused
    Given a project with a function and no coverage file
    When the crap4py command runs with existing coverage
    Then the crap4py command is refused with exit code 1 and an error naming the missing coverage file

  Scenario: crap4py 9 - absent coverage data reports every function as unmeasured
    Given a project with a function and a coverage command that writes no coverage file
    When the crap4py command runs with that coverage command
    Then the crap4py command succeeds with a warning that no coverage data was found and a report listing the function with coverage unmeasured and CRAP unmeasured

  Scenario: crap4py 10 - the coverage command receives the coverage file path
    Given a project with a function of complexity 1 whose lines are all covered
    When the crap4py command runs with a coverage command that writes the coverage file
    Then the crap4py command succeeds with a report listing the function with complexity 1, coverage 100.0%, and CRAP 1.0

  Scenario: crap4py 11 - a failing coverage command warns but still reports
    Given a project with a function of complexity 1 whose lines are all covered
    And a coverage command that writes the coverage file and then exits non-zero
    When the crap4py command runs with that coverage command
    Then the crap4py command succeeds with a warning that the coverage command exited non-zero and a report listing the function with CRAP 1.0

  Scenario: crap4py 12 - the default run uses the project test suite
    Given a project with a passing test suite and a function of complexity 1 whose lines the suite covers
    When the crap4py command runs without coverage flags
    Then the crap4py command succeeds with a report listing the function with coverage 100.0% and CRAP 1.0

  Scenario: crap4py 13 - a failing complexity source is refused
    Given a project with a coverage file whose complexity source fails
    When the crap4py command runs with existing coverage
    Then the crap4py command is refused with exit code 1 and an error naming the complexity failure

  Scenario: crap4py 14 - a malformed coverage file is refused
    Given a project with a coverage file whose data line precedes any source line
    When the crap4py command runs with existing coverage
    Then the crap4py command is refused with exit code 1 and an error saying the coverage file is malformed

  Scenario: crap4py 15 - an explicit coverage file path is read
    Given a project with a function of complexity 1 whose lines are all covered
    And a coverage file outside the default location
    When the crap4py command runs with existing coverage from the explicit coverage file
    Then the crap4py command succeeds with a report listing the function with coverage 100.0% and CRAP 1.0
