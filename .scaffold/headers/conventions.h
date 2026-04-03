// .scaffold/headers/conventions.h
// Coding conventions contract. AI follows these when generating code.

#ifndef CONVENTIONS_H
#define CONVENTIONS_H

#include "project.h"

#naming {
    files:      "snake_case",
    classes:    "PascalCase",
    functions:  "snake_case",
    variables:  "snake_case",
    constants:  "SCREAMING_SNAKE",
}

#patterns {
    architecture: "layered"          // compute → viz → imgui
    state:        "functional"       // pure functions where possible
    di:           "import-based"     // Python imports, no DI framework
    errors:       "exceptions"       // raise on invalid input, let caller handle
    async:        "none"             // synchronous; GPU dispatch is fire-and-wait
}

#file_structure {
    group_by: "feature"              // compute/math/, compute/fft/, viz/, viz/3d/, etc.
    test_location: "mirror"          // tests/ mirrors source structure (test_linalg.py, test_fft.py)
}

#rules [
    "No wildcard imports",
    "All public functions must have docstrings",
    "NumPy arrays preferred over Python lists for numeric data",
    "Type hints on all public function signatures",
    "Apache 2.0 compatible dependencies only — no GPL",
    "Platform targets: Linux (Wayland) and Windows 10/11 only",
    "C++ follows snake_case for functions, PascalCase for classes",
    "GLSL shaders use camelCase locals, SCREAMING_SNAKE for constants",
    "Tests use pytest with numpy.testing.assert_allclose for numeric comparisons",
]

#endif // CONVENTIONS_H
