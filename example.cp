int main(){
    float num = 3.14;
    if (num < 5) {
        print("if branch");
    } else {
        print("else branch");
    }
    while num < 10 {
        print(num);
        num = num + 1;
    }
    for(int i = 0; i < 3; i = i + 1) {
        print(i);
    }
    do {
        print("do-while");
        num = num - 1;
    } while num > 7;
    print(num);
    return 0;
}
