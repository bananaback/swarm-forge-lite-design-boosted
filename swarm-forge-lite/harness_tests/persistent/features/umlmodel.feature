Feature: umlmodel

  Background:
    Given no harness environment overrides

  Scenario: umlmodel 1 - the list op is the discovery entry
    When the uml tool runs the list op
    Then the op list names classes and add-class

  Scenario: umlmodel 2 - the stats op counts the classes
    Given a copy of a valid model
    When the uml tool runs the stats op
    Then the stats report counts 2 classes

  Scenario: umlmodel 3 - an add-class writes the class
    Given a copy of a valid model
    When the uml tool adds a class core.New to core
    Then the model holds a class core.New

  Scenario: umlmodel 4 - an add-edge writes the edge
    Given a copy of a valid model
    When the uml tool adds a class core.New to core
    And the uml tool adds an edge from shell.B to core.New
    Then the model holds the edge shell.B to core.New

  Scenario: umlmodel 5 - a mutation changes the bytes
    Given a copy of a valid model
    When the uml tool adds a class core.New to core
    And the uml tool adds an edge from shell.B to core.New
    Then the model file differs from the copy at the start

  Scenario: umlmodel 6 - the reverse returns the bytes
    Given a copy of a valid model
    When the uml tool adds a class core.New to core
    And the uml tool adds an edge from shell.B to core.New
    And the uml tool removes that class and its edge
    Then the model file is byte-identical to the copy at the start

  Scenario: umlmodel 7 - a dry run writes nothing
    Given a copy of a valid model
    When the uml tool adds a class core.New to core without writing
    Then the model file is byte-identical to the copy at the start

  Scenario: umlmodel 8 - a rejected op writes nothing
    Given a copy of a valid model
    When the uml tool tries to add an edge from core.A to core.Ghost
    Then the run is refused with exit code 2 and an error naming unknown to
    And the model file is byte-identical to the copy at the start

  Scenario: umlmodel 9 - the violations op finds an inner-to-outer dependency
    Given a copy of a valid model with an extra inner-to-outer dependency
    When the uml tool runs the violations op
    Then the violations report names core.A to shell.B

  Scenario: umlmodel 10 - the unassigned op warns on a class under no level
    Given a copy of a valid model with an unassigned class
    When the uml tool runs the unassigned op
    Then the unassigned report names tooling.X

  Scenario: umlmodel 11 - a rename rewrites the id and the edges
    Given a copy of a valid model
    When the uml tool renames core.A to core.Renamed
    Then the model holds a class core.Renamed
    And the model holds the edge shell.B to core.Renamed

  Scenario: umlmodel 12 - the check op passes a sound model
    Given a copy of a valid model
    When the uml tool runs the check op
    Then the check report exits with code 0

  Scenario: umlmodel 13 - the check op fails a bad edge
    Given a copy of a valid model with a bad edge
    When the uml tool runs the check op
    Then the check report exits with code 1
    And the check report names core.Ghost

  Scenario: umlmodel 14 - a new package does not survive its last class
    Given a copy of a valid model
    When the uml tool adds a class brandnew.Thing in the package brandnew
    And the uml tool removes the class brandnew.Thing
    Then the model file is byte-identical to the copy at the start
    And the model holds no package brandnew
