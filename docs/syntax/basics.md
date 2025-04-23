[← Back to Introduction](../introduction.md)

# C+ Language Fundamentals

## File Structure

C+ source files use the `.cp` file extension. Each file can contain multiple functions and class definitions, with execution beginning at the `main()` function.

## Program Entry Point

Every C+ application requires a `main()` function that serves as the program's entry point:

```cpp
int main() {
    // Application code
    return 0;
}
```

The `main()` function must return an integer value indicating the program's exit status. By convention, `0` indicates successful execution.

## Console Output

The `print()` function outputs text to the console:

```cpp
int main() {
    print("Hello, world!");
    return 0;
}
```

Output:
```
Hello, world!
```

## Variables and Data Types

C+ supports several primitive data types:

```cpp
int main() {
    // Integer type
    int count = 42;
    
    // Floating-point type
    float pi = 3.14159;
    
    // Character type
    char grade = 'A';
    
    // String type
    string message = "Welcome to C+";
    
    print(message + ": " + count);
    return 0;
}
```

## String Concatenation

Strings can be combined using the `+` operator:

```cpp
int main() {
    string firstName = "John";
    string lastName = "Doe";
    print("Full name: " + firstName + " " + lastName);
    return 0;
}
```

## Conditional Statements

C+ supports standard conditional logic with `if`, `else if`, and `else` statements:

```cpp
int main() {
    int age = 25;
    
    if (age < 18) {
        print("Minor");
    } else if (age >= 18 && age < 65) {
        print("Adult");
    } else {
        print("Senior");
    }
    
    return 0;
}
```

### Comparison Operators

C+ provides the following comparison operators:
- `==` - Equal to
- `!=` - Not equal to
- `<` - Less than
- `>` - Greater than
- `<=` - Less than or equal to
- `>=` - Greater than or equal to

## Loops

### While Loop

The `while` loop executes a block of code repeatedly while a condition is true:

```cpp
int main() {
    int i = 0;
    while (i < 5) {
        print("Iteration: " + i);
        i = i + 1;
    }
    return 0;
}
```

### For Loop

The `for` loop provides a more concise syntax for iteration:

```cpp
int main() {
    for (int i = 0; i < 5; i = i + 1) {
        print("Iteration: " + i);
    }
    return 0;
}
```

## Next Steps

Continue to [Functions and Procedures](./functions.md) to learn about defining and calling functions in C+.