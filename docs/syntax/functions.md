[← Back to Introduction](../introduction.md)

# C+ Functions

## Basics

In C+, functions are defined using the following syntax:

```cpp
return_type function_name(parameter_list) {
    // function body
}
```

* **return\_type**: The data type of the value the function returns (e.g., `int`, `double`, `string`).
* **function\_name**: The name you use to call the function.
* **parameter\_list**: A comma-separated list of input parameters, each with a type and a name.

### Example

```cpp

string concatenateStrings(string text1, string text2) {
    return text1 + text2;
}
```

In this example:

* `string` is the return type.
* `concatenateStrings` is the function name.
* The function takes two parameters of type `string` and returns their concatenation.

## Function Declarations

In C+, you can declare a function before defining it. This is especially useful when working with multiple source files or calling C functions.

### Syntax

```cpp
return_type function_name(parameter_list);
```

### Example Declaration

```cpp
string a_declared_function();
```

This tells the compiler that a function named `a_declared_function` exists and will return a `string`, even if its definition appears later in the code or in a different file.
