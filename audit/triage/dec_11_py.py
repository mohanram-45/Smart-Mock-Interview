from dec_helpers import *
def snip(prose, impl):
    return prose.strip()+"\n\n```python\n"+impl.strip()+"\n```"

X(4061,"PLACEHOLDER;MEANINGLESS","template text, not an answer")
K(4058,"M","THIN_ANSWER","correct; no example of a decorator")
K(4059,"E","","correct; CPython small-integer caching caveat not mentioned")
K(4060,"E","","correct")
K(4062,"E","THIN_ANSWER","correct; no example, else/raise not mentioned")
K(4063,"M","THIN_ANSWER","correct; amortised O(1)")
K(4064,"M","THIN_ANSWER","correct; cost of list.pop(0) (O(n)) not mentioned")

I4065='''a = [1, 2, 3]
b = a[::-1]          # new reversed list; a unchanged
c = list(reversed(a)) # iterator -> new list; a unchanged
a.reverse()          # in place; returns None'''
T4065='''
a=[1,2,3]; b=a[::-1]; c=list(reversed(a)); r=a.reverse()
assert b==[3,2,1] and c==[3,2,1] and a==[3,2,1] and r is None
'''
F(4065,"E","THIN_ANSWER;REQUIRES_CODE","does not state in-place vs copy distinction",
  pa=snip("list.reverse() reverses in place and returns None; slicing [::-1] returns a new reversed list; reversed() returns an iterator over the items in reverse order (wrap in list() for a list). Each is O(n); use reverse() to avoid a copy and slicing/reversed() to keep the original.",I4065),
  state="ready_for_approval",conf="high",code=I4065.replace("a.reverse() ","a.reverse() ")+T4065)

I4066='''class Node:
    def __init__(self, key):
        self.key, self.left, self.right = key, None, None

class BST:
    def __init__(self):
        self.root = None

    def insert(self, key):
        if self.root is None:
            self.root = Node(key)
            return
        cur = self.root
        while True:
            if key < cur.key:
                if cur.left is None:
                    cur.left = Node(key); return
                cur = cur.left
            elif key > cur.key:
                if cur.right is None:
                    cur.right = Node(key); return
                cur = cur.right
            else:
                return  # ignore duplicates

    def search(self, key):
        cur = self.root
        while cur:
            if key == cur.key:
                return True
            cur = cur.left if key < cur.key else cur.right
        return False

    def inorder(self):
        out, stack, cur = [], [], self.root
        while stack or cur:
            while cur:
                stack.append(cur); cur = cur.left
            cur = stack.pop(); out.append(cur.key); cur = cur.right
        return out'''
T4066='''
import random
t=BST()
vals=random.sample(range(1000),200)
for v in vals: t.insert(v)
assert t.inorder()==sorted(vals)
assert all(t.search(v) for v in vals) and not t.search(-5)
t.insert(vals[0]); assert t.inorder()==sorted(vals)
'''
F(4066,"H","DOES_NOT_ADDRESS;REQUIRES_CODE;IMPRECISE","asks for an implementation; answer only describes a BST; O(log n) holds only for balanced trees (O(n) worst case)",
  pa=snip("A BST stores keys so that every left descendant is smaller and every right descendant is larger. Search, insert and delete take O(h), where h is the height: O(log n) on average for random insertions but O(n) in the worst case (sorted input) unless the tree is self-balancing (AVL, red-black). Minimal implementation (no delete):",I4066),
  state="ready_for_approval",conf="high",code=I4066+T4066)

I4068='''def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out'''
T4068='''
r=fizzbuzz(15)
assert r[2]=="Fizz" and r[4]=="Buzz" and r[14]=="FizzBuzz" and r[0]=="1" and len(r)==15
assert fizzbuzz(0)==[]
'''
F(4068,"M","DOES_NOT_ADDRESS;REQUIRES_CODE","asks for an implementation; answer only restates the problem",
  pa=snip("Loop from 1 to n; test divisibility by 15 (or by 3 and 5) first, then 3, then 5, otherwise use the number. Checking the combined case first is the key detail.",I4068),
  state="ready_for_approval",conf="high",code=I4068+T4068)

I4069='''import heapq

def dijkstra(graph, source):
    """graph: {node: [(neighbour, weight), ...]} with non-negative weights."""
    dist = {node: float("inf") for node in graph}
    dist[source] = 0
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue  # stale entry
        for v, w in graph[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist'''
T4069='''
g={"A":[("B",1),("C",4)],"B":[("C",2),("D",5)],"C":[("D",1)],"D":[],"E":[]}
d=dijkstra(g,"A")
assert d["A"]==0 and d["B"]==1 and d["C"]==3 and d["D"]==4 and d["E"]==float("inf")
'''
F(4069,"H","DOES_NOT_ADDRESS;REQUIRES_CODE","asks for an implementation; answer only gives complexity",
  pa=snip("Dijkstra's algorithm finds shortest paths from a source to all nodes in a graph with non-negative edge weights. Use a min-heap keyed by distance; repeatedly pop the closest unfinalised node and relax its edges. With a binary heap it runs in O((V + E) log V). It fails with negative weights (use Bellman-Ford).",I4069),
  state="ready_for_approval",conf="high",code=I4069+T4069)

I4070='''def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    mid = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + mid + quicksort(right)'''
T4070='''
import random
for _ in range(50):
    a=[random.randint(-50,50) for _ in range(random.randint(0,60))]
    assert quicksort(a)==sorted(a)
'''
F(4070,"M","QUESTION_TYPO;REQUIRES_CODE","'Whats quicksort algorithm in Python.' is not a well-formed question; no implementation",
  pq="What is quicksort and how would you implement it in Python?",
  pa=snip("Quicksort is a divide-and-conquer sort: choose a pivot, partition the items into smaller, equal and larger groups, and recursively sort the outer groups. Average time is O(n log n); the worst case is O(n^2) (for example consistently bad pivots), and the in-place version uses O(log n) extra stack space on average. The version below favours clarity (it allocates new lists):",I4070),
  state="ready_for_approval",conf="high",code=I4070+T4070)
F(4071,"E","QUESTION_TYPO","'Whats bubble sort in Python.' is not a well-formed question",
  pq="What is bubble sort and what is its time complexity?",state="ready_for_approval",conf="high")
K(4072,"E","","correct")

I4073='''class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance'''
T4073='''
a=Singleton(); b=Singleton()
assert a is b
'''
F(4073,"M","QUESTION_TYPO;REQUIRES_CODE","question is a fragment; no Python implementation",
  pq="What is the Singleton pattern and how can you implement it in Python?",
  pa=snip("The Singleton pattern restricts a class to one instance and provides global access to it, e.g. for configuration, logging or connection pools. In Python the simplest singleton is a module-level object (modules are imported once); alternatively override __new__ as below. Caveats: it is global state, makes testing harder, and the simple version is not thread-safe.",I4073),
  state="ready_for_approval",conf="high",code=I4073+T4073)

I4074='''class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return f"{self.name} makes a sound"

class Dog(Animal):
    def speak(self):               # method overriding
        return f"{self.name} barks"

class Cat(Animal):
    def __init__(self, name, indoor=True):
        super().__init__(name)     # reuse parent initialiser
        self.indoor = indoor'''
T4074='''
assert Dog("Rex").speak()=="Rex barks"
assert Cat("Tom").speak()=="Tom makes a sound" and Cat("Tom").indoor is True
assert isinstance(Dog("a"),Animal) and issubclass(Cat,Animal)
'''
F(4074,"M","DOES_NOT_ADDRESS;REQUIRES_CODE","asks for an example; none given",
  pa=snip("Inheritance lets a child class reuse and extend a parent class: it inherits attributes and methods, can override them, and can call the parent's version with super(). It models an 'is-a' relationship and promotes reuse; Python also supports multiple inheritance (resolved with the MRO).",I4074),
  state="ready_for_approval",conf="high",code=I4074+T4074)

F(4075,"M","REQUIRES_CODE;LOW_RELEVANCE","answer contains no code; web development is outside the six interview domains",
  state="needs_code_test",conf="low")
X(4076,"PLACEHOLDER;MEANINGLESS","template text, not an answer")
F(4077,"H","REQUIRES_CODE;SECURITY_SENSITIVE;LOW_RELEVANCE","asks for an implementation; answer only defines JWT. Authentication code is security-sensitive and not verified here; outside the six interview domains",
  state="needs_review",conf="low")

I4078='''import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5]
y = [2, 4, 5, 4, 5]
plt.scatter(x, y, c="tab:blue", s=40, alpha=0.8, label="samples")
plt.xlabel("x"); plt.ylabel("y"); plt.title("Scatter plot")
plt.legend()
plt.show()'''
T4078='''
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig,ax=plt.subplots()
sc=ax.scatter([1,2,3],[3,2,1],s=40)
assert len(sc.get_offsets())==3
'''
F(4078,"M","DOES_NOT_ADDRESS;REQUIRES_CODE","asks how; answer names scatter() but gives no usage",
  pa=snip("Call plt.scatter(x, y) (or ax.scatter on an Axes); useful options are c (colour or values), s (marker size), alpha (transparency) and label. Add axis labels, a title and optionally a legend, then show or save the figure.",I4078),
  state="ready_for_approval",conf="high",code=T4078)
K(4079,"E","THIN_ANSWER","correct but names no methods (isna, dropna, fillna, ffill/bfill, interpolate)")

I4080='''import numpy as np

def fit_linear_regression(X, y):
    """Ordinary least squares via the normal equation; adds an intercept."""
    X = np.asarray(X, dtype=float).reshape(len(X), -1)
    Xb = np.c_[np.ones(len(X)), X]
    theta = np.linalg.pinv(Xb.T @ Xb) @ Xb.T @ np.asarray(y, dtype=float)
    return theta  # theta[0] = intercept, theta[1:] = coefficients

def predict(theta, X):
    X = np.asarray(X, dtype=float).reshape(len(X), -1)
    return np.c_[np.ones(len(X)), X] @ theta'''
T4080='''
rng=np.random.default_rng(0)
X=rng.normal(size=(200,2)); y=3+2*X[:,0]-1.5*X[:,1]+rng.normal(scale=0.01,size=200)
th=fit_linear_regression(X,y)
assert np.allclose(th,[3,2,-1.5],atol=0.05)
assert np.allclose(predict(th,X),y,atol=0.05)
'''
F(4080,"H","DOES_NOT_ADDRESS;REQUIRES_CODE","asks for an implementation; answer only describes the method",
  pa=snip("Linear regression picks the parameters that minimise the sum of squared errors. With a design matrix Xb (including a column of ones), the closed-form (normal-equation) solution is theta = (Xb^T Xb)^-1 Xb^T y; gradient descent is the alternative for large or high-dimensional data. Implementation:",I4080),
  state="ready_for_approval",conf="high",code=I4080+T4080)

F(4081,"M","REQUIRES_CODE","answer is a definition; no pytest example. pytest is not installed in the audit sandbox, so no example could be executed",
  state="needs_code_test",conf="low")

I4083='''import unittest

def add(a, b):
    return a + b

class TestAdd(unittest.TestCase):
    def test_add_positive(self):
        self.assertEqual(add(2, 3), 5)

    def test_add_negative(self):
        self.assertEqual(add(-1, 1), 0)

if __name__ == "__main__":
    unittest.main()'''
T4083='''
import unittest
suite=unittest.defaultTestLoader.loadTestsFromTestCase(TestAdd)
res=unittest.TextTestRunner(verbosity=0).run(suite)
assert res.wasSuccessful() and res.testsRun==2
'''
F(4083,"E","THIN_ANSWER;REQUIRES_CODE","no example",
  pa=snip("Import unittest, subclass unittest.TestCase and write methods whose names start with 'test', using assertion methods such as assertEqual, assertTrue and assertRaises. Run with python -m unittest (or pytest).",I4083),
  state="ready_for_approval",conf="high",code=I4083.replace('if __name__ == "__main__":\n    unittest.main()','')+T4083)

I4084='''import asyncio

async def fetch(name, delay):
    await asyncio.sleep(delay)        # stands in for an I/O call
    return f"{name} done"

async def main():
    results = await asyncio.gather(
        fetch("a", 1), fetch("b", 1), fetch("c", 1)
    )
    return results                    # takes about 1 second, not 3

# asyncio.run(main())'''
T4084='''
import time
t=time.time()
r=asyncio.run(main())
dt=time.time()-t
assert r==["a done","b done","c done"] and dt<2.0
'''
F(4084,"H","DOES_NOT_ADDRESS;REQUIRES_CODE","asks for an implementation; answer only explains the keywords",
  pa=snip("async def defines a coroutine; await suspends it until an awaitable finishes, letting the event loop run other tasks. asyncio.gather (or tasks created with asyncio.create_task) runs coroutines concurrently, which helps I/O-bound work but not CPU-bound work. Example:",I4084),
  state="ready_for_approval",conf="high",code=I4084+T4084)

I4085='''def fibonacci(limit):
    a, b = 0, 1
    while a < limit:
        yield a
        a, b = b, a + b'''
T4085='''
import types
g=fibonacci(50)
assert isinstance(g,types.GeneratorType)
assert list(g)==[0,1,1,2,3,5,8,13,21,34]
'''
F(4085,"M","DOES_NOT_ADDRESS;REQUIRES_CODE","asks for an implementation; answer only describes generators",
  pa=snip("A generator function contains yield; calling it returns an iterator that produces values lazily, pausing at each yield and resuming where it left off, so it uses constant memory even for huge or infinite sequences. Example:",I4085),
  state="ready_for_approval",conf="high",code=I4085+T4085)
K(4067,"E","","correct")
X(4082,"PLACEHOLDER;MEANINGLESS","generic restatement; 'Testing Debugging' is a template topic, not a question")
