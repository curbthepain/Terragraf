// .scaffold/headers/conventions.h
// Coding conventions contract. AI follows these when generating code.

#ifndef CONVENTIONS_H
#define CONVENTIONS_H

#include "project.h"

#naming {
    files:      "",     // "snake_case", "kebab-case", "PascalCase"
    classes:    "",     // "PascalCase"
    functions:  "",     // "camelCase", "snake_case"
    variables:  "",     // "camelCase", "snake_case"
    constants:  "",     // "SCREAMING_SNAKE"
}

#patterns {
    // architecture: "MVVM"
    // state:        "unidirectional"
    // di:           "constructor-injection"
    // errors:       "result-type"
    // async:        "coroutines"
}

#file_structure {
    // group_by: "feature"       // vs "type"
    // test_location: "colocated" // vs "mirror"
}

#rules [
    // "No wildcard imports"
    // "All public functions must have doc comments"
]

#endif // CONVENTIONS_H
