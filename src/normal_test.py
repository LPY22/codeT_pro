class MyClass:
    def __init__(self):
        self._my_variable = 0  # 定义一个私有属性

    def _helper_function(self):
        print("This is a helper function")

    def public_method(self):
        print("This is a public method")
        self._helper_function()  # 在类内部可以调用私有函数

my_object = MyClass()
my_object.public_method()  # 可以调用公有方法
my_object._helper_function()#也可以直接调用
compile("a = 10")