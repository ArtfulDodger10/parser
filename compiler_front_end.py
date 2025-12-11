import re
import sys

# --- (SCANNER) CODE ---

TOKEN_TYPES = {
    'KEYWORD': r'\b(?:int|float|double|char|return|if|else|for|while|namespace|template|include|define)\b',
    'IDENTIFIER': r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
    'PREPROCESSOR': r'#\s*(?:include|define)\b',
    'CONSTANT_FLOAT': r'\b\d+\.\d+\b',
    'CONSTANT_INT': r'\b\d+\b',
    # Updated OPERATOR to include '<<' and '>>'
    'OPERATOR': r'(==|!=|<=|>=|\+\+|--|\+=|-=|\*=|/=|&&|\|\||<<|>>|[+\-*/=<>!&|%^~])',
    'PUNCTUATOR': r'[{}();,<>]',
    'STRING_LITERAL': r'"(?:\\.|[^"\\])*"',
    'COMMENT_SINGLE': r'//.*',
    'COMMENT_MULTI': r'/\*[\s\S]*?\*/',
}


class Lexer:
    def __init__(self, code):
        self.code = code
        self.tokens = []

    def tokenize(self):
        # 1. Remove comments first
        self.code = re.sub(TOKEN_TYPES['COMMENT_MULTI'], '', self.code)
        self.code = re.sub(TOKEN_TYPES['COMMENT_SINGLE'], '', self.code)

        while self.code:
            self.code = self.code.lstrip()
            if not self.code:
                break
                
            matched = False
            
            for token_type, pattern in TOKEN_TYPES.items():
                if token_type in ['COMMENT_SINGLE', 'COMMENT_MULTI']:
                    continue
                    
                match = re.match(pattern, self.code)
                if match:
                    value = match.group(0)
                    self.tokens.append((token_type, value))
                    self.code = self.code[match.end():]
                    matched = True
                    break

            if not matched:
                # Lexical Error: Skip unknown or invalid character
                self.code = self.code[1:]

        return self.tokens

# --- PARSER CODE ---

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.token_index = 0
        self.current_token = self.tokens[0] if self.tokens else None
        self.errors = []

    def consume(self):
        """Advance to the next token."""
        self.token_index += 1
        if self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]
        else:
            self.current_token = None

    def match(self, expected_type, expected_value=None):
        """Check if the current token matches the expected type and value, then consume it."""
        if self.current_token is None:
            self.error(f"Expected {expected_type} {f'({expected_value})' if expected_value else ''}, but found end of file.")
            return False

        token_type, token_value = self.current_token
        
        type_match = token_type == expected_type
        value_match = expected_value is None or token_value == expected_value

        if type_match and value_match:
            self.consume()
            return True
        else:
            expected_str = f"{expected_type} {f'({expected_value})' if expected_value else ''}"
            self.error(f"Expected {expected_str}, but found <{token_type}, {token_value}>.")
            return False

    def error(self, message):

        self.errors.append(f"Syntax Error at token index {self.token_index}: {message}")
        
    def parse(self):
        try:
            self.program()
            if self.current_token is not None:
                self.error(f"Unexpected token <{self.current_token[0]}, {self.current_token[1]}> after program end.")
        except Exception as e:
            pass
            
        if not self.errors:
            return True
        else:
            return False




    def program(self):
        self.function_definition()


    def function_definition(self):
        self.type()
        self.match('IDENTIFIER')
        self.match('PUNCTUATOR', '(')
        self.match('PUNCTUATOR', ')')
        self.block()


    def type(self):
        if self.current_token and self.current_token[0] == 'KEYWORD' and self.current_token[1] in ['int', 'float', 'double', 'char']:
            self.consume()
        else:
            self.error("Expected a Type (int, float, double, char).")


    def block(self):
        self.match('PUNCTUATOR', '{')
        self.statement_list()
        self.match('PUNCTUATOR', '}')


    def statement_list(self):
        while self.current_token and self.current_token[1] not in ['}']:
            self.statement()
            if self.errors:
                break


    def statement(self):
        if self.current_token is None:
            return

        token_type, token_value = self.current_token
        
        if token_type == 'KEYWORD' and token_value in ['int', 'float', 'double', 'char']:
            self.declaration_statement()
            self.match('PUNCTUATOR', ';')
        elif token_type == 'IDENTIFIER':

            if self.token_index + 1 < len(self.tokens):
                next_token_value = self.tokens[self.token_index + 1][1]
                next_token_type = self.tokens[self.token_index + 1][0]
                
                if next_token_value == '=':
                    self.assignment_statement()
                    self.match('PUNCTUATOR', ';')
                elif next_token_type == 'OPERATOR' and next_token_value == '<<':
                    self.output_statement()
                    self.match('PUNCTUATOR', ';')
                else:
                    self.error("Expected AssignmentStatement or OutputStatement.")
            else:
                self.error("Expected AssignmentStatement or OutputStatement, but found end of file.")
                
        elif token_type == 'KEYWORD' and token_value == 'if':
            self.if_statement()
        elif token_type == 'KEYWORD' and token_value == 'return':
            self.return_statement()
            self.match('PUNCTUATOR', ';')
        else:
            self.error("Expected a valid Statement (Declaration, Assignment, If, Output, or Return).")
            self.consume()



    def declaration_statement(self):
        self.type()
        self.identifier_list()


    def identifier_list(self):
        self.match('IDENTIFIER')
        while self.current_token and self.current_token[1] == ',':
            self.match('PUNCTUATOR', ',')
            self.match('IDENTIFIER')


    def assignment_statement(self):
        self.match('IDENTIFIER')
        self.match('OPERATOR', '=')
        self.expression()


    def if_statement(self):
        self.match('KEYWORD', 'if')
        self.match('PUNCTUATOR', '(')
        self.condition()
        self.match('PUNCTUATOR', ')')
        self.block()
        
        if self.current_token and self.current_token[1] == 'else':
            self.match('KEYWORD', 'else')
            self.block()


    def condition(self):
        self.expression()
        self.compare_op()
        self.expression()


    def compare_op(self):
        if self.current_token and self.current_token[0] == 'OPERATOR' and self.current_token[1] in ['==', '!=', '<', '>', '<=', '>=']:
            self.consume()
        else:
            self.error("Expected a Comparison Operator (==, !=, <, >, <=, >=).")


    def output_statement(self):
        self.match('IDENTIFIER') # Should be 'cout'
        self.output_list()


    def output_list(self):
        self.match('OPERATOR', '<<')
        self.output_item()
        
        while self.current_token and self.current_token[1] == '<<':
            self.match('OPERATOR', '<<')
            self.output_item()

    # OutputItem -> STRING_LITERAL | IDENTIFIER | "endl"
    def output_item(self):
        if self.current_token is None:
            self.error("Expected an Output Item (String, Identifier, or endl).")
            return
            
        token_type, token_value = self.current_token
        
        if token_type == 'STRING_LITERAL':
            self.consume()
        elif token_type == 'IDENTIFIER':
            # Check for 'endl' which is treated as a special identifier in the grammar
            if token_value == 'endl':
                self.consume()
            else:
                self.consume() # It's a variable identifier
        else:
            self.error("Expected a String Literal, Identifier, or 'endl'.")

    # ReturnStatement -> "return" Expression
    def return_statement(self):
        self.match('KEYWORD', 'return')
        self.expression()

    # Expression -> Term { ("+" | "-") Term }
    def expression(self):
        self.term()
        while self.current_token and self.current_token[1] in ['+', '-']:
            self.consume() # Consume '+' or '-'
            self.term()

    # Term -> Factor { ("*" | "/") Factor }
    def term(self):
        self.factor()
        while self.current_token and self.current_token[1] in ['*', '/']:
            self.consume() # Consume '*' or '/'
            self.factor()

    # Factor -> IDENTIFIER | CONSTANT_INT | CONSTANT_FLOAT | "(" Expression ")"
    def factor(self):
        if self.current_token is None:
            self.error("Expected Factor (Identifier, Constant, or '(' Expression ')').")
            return
            
        token_type, token_value = self.current_token
        
        if token_type == 'IDENTIFIER' or token_type == 'CONSTANT_INT' or token_type == 'CONSTANT_FLOAT':
            self.consume()
        elif token_value == '(':
            self.match('PUNCTUATOR', '(')
            self.expression()
            self.match('PUNCTUATOR', ')')
        else:
            self.error("Expected Factor (Identifier, Constant, or '(' Expression ')').")
            
# --- MAIN EXECUTION ---

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python compiler_front_end.py source_file.c")
        sys.exit(1)

    source_file_path = sys.argv[1]
    
    try:
        # Read input source file
        with open(source_file_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: Source file not found at {source_file_path}")
        sys.exit(1)

    # 1. Lexical Analysis (Scanning)
    print("--- Lexical Analysis (Scanning) ---")
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    
    if not tokens:
        print("Error: No tokens generated from the source file.")
        sys.exit(1)
        
    for token_type, token_value in tokens:
        print(f"<{token_type}, {token_value}>")
    
    print("\n" + "="*30 + "\n")
    
    # 2. Syntactic Analysis (Parsing)
    print("--- Syntactic Analysis (Parsing) ---")
    parser = Parser(tokens)
    is_valid = parser.parse()

    # 3. Report Results
    if is_valid:
        print("Parsing successful! No syntax errors found.")
    else:
        print("Parsing failed! Syntax errors found:")
        for error in parser.errors:
            print(f"- {error}")
