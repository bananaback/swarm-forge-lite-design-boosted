Feature: dryer

  Background:
    Given no harness environment overrides

  Scenario: dryer 1 - similar-sized functions below the threshold are not reported
    Given a project whose source holds two functions below the similarity threshold
    When the dry tool runs over the source
    Then the dry report counts 0 pairs

  Scenario: dryer 2 - a duplicated function is reported as one pair
    Given a project with a duplicated function in alpha.py and beta.py
    When the dry tool runs over the source
    Then the dry report counts 1 pair

  Scenario: dryer 3 - the pair names both files
    Given a project with a duplicated function in alpha.py and beta.py
    When the dry tool runs over the source
    Then the dry report names alpha.py and beta.py

  Scenario: dryer 4 - the pair carries both positions
    Given a project with a duplicated function in alpha.py and beta.py
    When the dry tool runs over the source
    Then the dry report lists a pair from alpha.py lines 1-5 to beta.py lines 1-5

  Scenario: dryer 5 - a minimum line count above the form size drops it
    Given a project with a duplicated function in alpha.py and beta.py
    When the dry tool runs over the source with minimum lines 6
    Then the dry report counts 0 pairs

  Scenario: dryer 6 - a lowered threshold reports the near pair
    Given a project whose source holds two functions below the similarity threshold
    When the dry tool runs over the source with similarity threshold 0.5
    Then the dry report counts 1 pair

  Scenario: dryer 7 - the run writes the dry.edn snapshot under the artifacts root
    Given a project with a duplicated function in alpha.py and beta.py
    When the dry tool runs over the source
    Then the artifacts hold a dry.edn snapshot naming python
    And the source directory holds no .metrics directory
