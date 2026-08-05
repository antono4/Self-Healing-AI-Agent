"""Sample buggy code for demonstration."""

def calculate_division(a, b):
    """Divide a by b."""
    result = a / b  # This will fail if b is 0
    return result


def process_list(items):
    """Process a list of items."""
    total = 0
    for item in items:
        total += int(item)  # This will fail if item is not convertible
    return total


def get_value(data, key):
    """Get value from dictionary."""
    return data[key]  # This will fail if key doesn't exist


def add_numbers(a, b):
    """Add two numbers."""
    return a + b  # This will fail if types are incompatible


class Calculator:
    """Simple calculator class."""

    def __init__(self):
        self.result = 0

    def add(self, value):
        """Add value to result."""
        return self.result + value

    def multiply(self, value):
        """Multiply result by value."""
        return self.result * value


def main():
    """Main function."""
    # These will cause bugs
    print(calculate_division(10, 0))  # ZeroDivisionError

    print(process_list(["1", "2", "abc"]))  # ValueError

    data = {"name": "John"}
    print(get_value(data, "age"))  # KeyError

    print(add_numbers("string", 123))  # TypeError

    calc = Calculator()
    print(calc.add(None))  # TypeError


if __name__ == "__main__":
    main()
