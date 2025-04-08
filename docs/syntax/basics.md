[Back to introdurction](../introduction.md)
# Chapter 1.1: The basics of the syntax

So, first you have to create a source file, that ends with `.cp`, this is the file where you can write your code

## Your first line of C+ code
so first you have to create a main function, like most of the other languages:

```cp
// yourfirstfile.cp

int main(){
    // your code here
}
```
this is an example of a C+ file, so, lets go to the next, for your first hello world

## A simple hello world in C+
So, you can use `print("any text to print");` for printing to the console

```cp
// yourfirstfile.cp

int main(){
    print("Hello World!!!");
}
```
This will output:
```
Hello World
```

## Variables
So, you know how to print to the console, but if you want some dynamic, you can use variables
```cp
int main(){
    string name = "Homer";
    print("Hello " + name + "!"); // please correct me
                                  // I am a contributor
}
```

## If-else (simple conditions)
C+ has some conditions, if you want to check something

```cp
int main(){
    int age = 13;
    if (age < 18){
        print("You are not old enougth");
    } else {
        print("You are old enougth");
    }
}
```
So, you can use these operators: `==`, `!=`, `<=`, `>=`, `<` and `>`

## Next chapter: coming soon