// This file is part of the C+ project.
//
// Copyright (C) 2025 GiladLeef
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
// import code from other files using:
// import file.cp

class Person {
    string name;
    int age;

    int whatIsMyAge() {
        return self.age;
    }
}

int main() {
    float num = 3.14;

    if (num < 5) {
        print("if branch");
    } else {
        print("else branch");
    }

    while (num < 10) {
        print(num);
        num = num + 1;
    }

    for (int i = 0; i < 3; i = i + 1) {
        print(i);
    }

    do {
        print("do-while");
        num = num - 1;
    } while (num > 7);

    print(num);

    Person p;
    p.name = "John";
    p.age = 100;

    print(p.name);
    print(p.whatIsMyAge());

    int[5] numbers;
    numbers[0] = 10;
    numbers[1] = 20;
    numbers[2] = 30;
    numbers[3] = 40;
    numbers[4] = 50;
    
    print("Array elements:");
    for (int i = 0; i < 5; i = i + 1) {
        print(numbers[i]);
    }
    
    string[3] fruits;
    fruits[0] = "Apple";
    fruits[1] = "Banana";
    fruits[2] = "Cherry";
    
    print("Fruits:");
    for (int i = 0; i < 3; i = i + 1) {
        print(fruits[i]);
    }
    
    Person alice;
    alice.name = "Alice";
    alice.age = 25;
    
    Person bob;
    bob.name = "Bob";
    bob.age = 30;
    
    Person[2] people;
    people[0] = alice;
    people[1] = bob;
    
    print("People:");
    for (int i = 0; i < 2; i = i + 1) {
        Person current = people[i];
        print(current.name);
        print(current.whatIsMyAge());
    }

    return 0;
}
