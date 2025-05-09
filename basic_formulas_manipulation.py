from functools import partialmethod
import re

from lark import Tree, Token, Transformer
from lark.visitors import Visitor, Interpreter, Discard

from model import prover9_parser, Signature, Model, P9ModelReader

from PrettyPrint import PrettyPrintTree
import ansi2html

import logging
my_logger = logging.getLogger("my_logger")
logging.basicConfig(level=logging.INFO)


BINARY_OPS = [
    "conjunction",
    "disjunction",
    "conjunction_exc",
    "disjunction_exc",
    "entailment",
    "reverse_entailment",
    "equivalence_entailment",
    "entailment_exc",
    "reverse_entailment_exc",
    "equivalence_entailment_exc",
]


def getChildren(x):
    return x.children if hasattr(x, "children") else None


def getData(x):
    return x.data if hasattr(x, "data") else str(x)


def getExplanation(x):
    if hasattr(x, "explanation"):
        return f"{x.data} is {str(x.explanation).replace("'","").replace(": ",":")}"
    if hasattr(x, "additional_data"):
        return f"{x.data} --- {x.additional_data}"
    if hasattr(x, "data"):
        return x.data
    return str(x)
    # return (f"{x.data} is {x.explanation}" if hasattr(x, "explanation") else (x.data if hasattr(x,"data") else str(x)))


from colorama import Back

treeExplainer = PrettyPrintTree(getChildren, getExplanation, color="")
treeExplainerRED = PrettyPrintTree(getChildren, getExplanation, color=Back.RED)
treeExplainerGREEN = PrettyPrintTree(getChildren, getExplanation, color=Back.GREEN)
treeExplainerYELLOW = PrettyPrintTree(getChildren, getExplanation, color=Back.YELLOW)
treeExplainerReturning = PrettyPrintTree(
    getChildren, getExplanation, return_instead_of_print=True, color=""
)
treeExplainerReturningRED = PrettyPrintTree(
    getChildren, getExplanation, return_instead_of_print=True, color=Back.RED
)
treeExplainerReturningGREEN = PrettyPrintTree(
    getChildren, getExplanation, return_instead_of_print=True, color=Back.GREEN
)

ansi2htmlConverter = ansi2html.Ansi2HTMLConverter()

text0 = (
    "(all X (cat(X) <-> (ed(X) & (exists T pre(X,T)) & all T (pre(X,T) -> tat(X,T)))))."
)
# text = '(all X (cat(X) <-> (ed(X) & (exists T1 (pre(X,T1))) & all T (pre(X,T) -> tat(X,T))))).'
# text = '(A(c) & B(y)).'
# text = '(P(c1,c2) & Q(x) & T(v)) .'
# text = '''(P(c1,c2) & Q(x) & T(v)) .
# Q(c)    . '''
# text = '''(P(c1,c2) & Q(x) & T(v)) .
#             True    .
#             (P(c, c4) & True)    .
#             False    . '''
# text = 'all X A(X,Y) .'
text6 = "all X A(X,Y,c2) ."
text4 = "all X A(X,Y) & exists Z P(Z) ."
text5 = "all X A(X,Y,c2) & P(X,Z,c) ."
text3 = "all X all Y exists V A(X,Y,c2) & exists Z P(X,Z,c) | V(V,C,T,l)."
text2 = "all X A(X,Y,c2) | - exists Z P(X,Z,c) ."
text2pre = "all X all Z A(X,Y,c2) | - P(X,Z,c) ."
text1 = "all X all Y all Z all T all T2 A(X,Y,T) & A(Y,Z,T2) & B(T,T2) -> A(X,Z,T) ."
text7 = "all A all B all C all T all T2  ((((properContinuantPartOf(A,B,T)) & (properContinuantPartOf(B,C,T2)) & (temporalPartOf(T,T2)))) -> (properContinuantPartOf(A,C,T))) # label(\"proper-continuant-part-of-transitive-at-a-time\")."
text7 = "all A (B(A)) # label(\"proper-continuant-part-of-transitive-at-a-time\")."



# ast = prover9_parser.parse(text7)
# treeExplainer(ast)
# # treeExplainer(RemoveLines().transform(ast))
# exit()



class ToString(Interpreter):
    """Transform a tree into a formatted string"""

    def print_binary_op(self, tree, op: str):
        left, right = tree.children
        yes_left_par = left.data not in ["predicate", "equality_atom"]
        yes_right_par = right.data not in ["predicate", "equality_atom"]
        return (
            "(" * yes_left_par
            + self.visit(left)
            + ")" * yes_left_par
            + f" {op} "
            + "(" * yes_right_par
            + self.visit(right)
            + ")" * yes_right_par
        )

    entailment = partialmethod(print_binary_op, op="->")
    reverse_entailment = partialmethod(print_binary_op, op="<-")
    equivalence_entailment = partialmethod(print_binary_op, op="<->")
    disjunction = partialmethod(print_binary_op, op="|")
    conjunction = partialmethod(print_binary_op, op="&")
    entailment_exc = entailment
    equivalence_entailment_exc = reverse_entailment
    equivalence_entailment_exc = equivalence_entailment
    disjunction_exc = disjunction
    conjunction_exc = conjunction

    def negation(self, tree):
        negated_formula = tree.children[0]
        return f"-({self.visit(negated_formula)})"

    negation_exc = negation

    def print_quantification_op(self, tree, op: str):
        variable, quantified_formula = tree.children
        return f"{op} {variable} ({self.visit(quantified_formula)})"

    universal_quantification = partialmethod(print_quantification_op, op="all")
    existential_quantification = partialmethod(print_quantification_op, op="exists")

    def print_bounded_quantification_op(self, tree, op: str):
        variable, bounding_formula, quantified_formula = tree.children
        return f"{op} ({variable} ∈ {{{variable} | {self.visit(bounding_formula)}}}) ({self.visit(quantified_formula)})"

    universal_quantification_bounded = partialmethod(
        print_bounded_quantification_op, op="all"
    )
    existential_quantification_bounded = partialmethod(
        print_bounded_quantification_op, op="exists"
    )

    def equality_atom(self, tree):
        left, right = tree.children
        return f"{str(left)} = {str(right)}"

    def predicate(self, tree):
        predicate_symbol, *term_list = tree.children
        return f"{predicate_symbol}({",".join([term.value if hasattr(term, "value") else str(term) for term in term_list])})"

    def VARIABLE(self, tree):
        return str(tree)

    def true(self, tree):
        return "True"

    def false(self, tree):
        return "False"

    def empty(self, tree):
        return "empty"
    def cond(self, tree):
        return "cond"
    def dom(self, tree):
        return f"dom({tree.children[0]})"

    def pass_par_rule(self, tree, par: str):
        return Tree(Token("RULE", par), self.visit_children(tree))

    def pass_par(self, tree, par: str):
        return Tree(par, self.visit_children(tree))

    def start(self, tree):
        return self.visit(tree.children[0])

    def lines(self, tree):
        line_s: list = tree.children
        visited_line_s: list[str] = [self.visit(line) for line in line_s]
        return "\n".join(visited_line_s)

    def line(self, tree):
        formula = tree.children[0]
        return f"({self.visit(formula)})."
    
class P9FreeVariablesExtractor(Transformer):
    """Extract all free variables and predicates from a formula. E.g. all X A(X,Y,c2) | - exists Z P(X,Z,c) .  ---> {X}; {A:3, P:3, c:0, c2:0}
    Can be used repeatedly on different formulas.
    Calling transform returns just the variables, calling extract_free_variables_and_signature returns the variables and the signature"""

    def __init__(self, visit_tokens=True):
        super().__init__(visit_tokens)
        self.axioms_signature = Signature()
        
    # def transform(self, tree):
    #     # print(f"gonna transform {tree}{treeExplainerGREEN(tree)}")
    #     return super().transform(tree)

    def extract_free_variables_and_signature(
        self, tree: Tree
    ) -> tuple[set[str], Signature]:
        out_vars = self.transform(tree)
        out_signature = self.axioms_signature
        self.axioms_signature = Signature()
        return out_vars, out_signature

    def equality_atom(self, items):
        left_member, right_member = items
        variables_set: set[str] = set()
        self.axioms_signature.add_predicate("=", 2)
        if not isinstance(left_member, Token) or not isinstance(right_member, Token):
            raise AssertionError(
                f"Either the left member or the right member of the equality atom {items} is not a Token. This should never happen"
            )
        if left_member.type == "VARIABLE":
            variables_set.add(str(left_member))
        elif left_member.type == "CONSTANT":
            self.axioms_signature.add_constant(left_member)
        if right_member.type == "VARIABLE":
            variables_set.add(str(right_member))
        elif right_member.type == "CONSTANT":
            self.axioms_signature.add_constant(right_member)
        return variables_set

    def predicate(self, items):
        predicate_symbol, *term_list = items
        predicate_symbol = str(predicate_symbol)
        variable_set: set[str] = set()
        for token in term_list:
            if not isinstance(token, Token):
                # Now this can happen when using polarity...
                if isinstance(token, dict) and "polarity" in token.keys():
                    pass  # it's ok, do nothing
                else:  # unrecognized case
                    raise AssertionError(
                        f"Found non-token {token} in predicate {predicate_symbol} (and the non-token is not auxillary data about polarity). This should not happen"
                    )
            else:
                if token.type == "CONSTANT":
                    self.axioms_signature.add_constant(token)
                if token.type == "VARIABLE":
                    variable_set.add(str(token))
        self.axioms_signature.add_predicate(predicate_symbol, arity := len(term_list))
        return variable_set

    def quantification(self, items, thereIsBound=False):
        if thereIsBound:
            quantified_variable, bound, variables_from_inner_formula = items
            quantified_variables = [quantified_variable]
        else:
            *quantified_variables, variables_from_inner_formula = items
        if not all(isinstance(quantified_variable, (Token, str)) for quantified_variable in quantified_variables) or not isinstance(
            variables_from_inner_formula, set
        ):
            raise TypeError(
                f"Something wrong with returned variables: either the list of quantified variables(={quantified_variables}) or the variables from the inner formula (={variables_from_inner_formula})"
            )
        difference = variables_from_inner_formula.difference({str(quantified_variable) for quantified_variable in quantified_variables})
        return difference

    existential_quantification = quantification
    universal_quantification = quantification
    existential_quantification_bounded = partialmethod(
        quantification, thereIsBound=True
    )
    universal_quantification_bounded = partialmethod(quantification, thereIsBound=True)

    def empty(self, items):
        return set()
    def cond(self, items):
        return set() # check if correct TODO

    def dom(self, items):
        ranged_variable = items[0]
        return {str(ranged_variable)}

    # merge_variables = lambda self, items: set().union(*(var_set for var_set in items))
    def merge_variables(self, items):
        return set().union(*(var_set for var_set in items))

    conjunction = merge_variables
    disjunction = merge_variables
    conjunction_exc = merge_variables
    disjunction_exc = merge_variables
    entailment = merge_variables
    reverse_entailment = merge_variables
    equivalence_entailment = merge_variables
    entailment_exc = merge_variables
    reverse_entailment_exc = merge_variables
    equivalence_entailment_exc = merge_variables
    negation = merge_variables
    negation_exc = merge_variables

    true = empty
    false = empty

    do_nothing = lambda self, items: items
    car = lambda self, items: items[0]
    start = car
    lines = car
    line = car
    sentence = car

    label = lambda self, items: None

class AssociativeFlattener(Transformer):
    """flattens associative/commutative operations in a tree. E.g. (A & (B & C)) will become (A & B & C). all X all Y phi(X,Y) will become all {X Y} phi(X,Y). Also double negation will be removed"""

    def __init__(self, visit_tokens=False):
        super().__init__(visit_tokens)

    def transform_repeatedly(self, tree):
        oldtree = tree
        newtree = self.transform(oldtree)
        while newtree != oldtree:
            oldtree = newtree
            newtree = self.transform(newtree)
        return newtree

    def flatten_and_or(self, items, op: str):
        new_items = []
        for item in items:
            if item.data in [op, op + "_exc"]:
                new_items.extend(item.children)
            else:
                new_items.append(item)
        return Tree(op, new_items)

    conjunction = conjunction_exc = partialmethod(flatten_and_or, op="conjunction")
    disjunction = disjunction_exc = partialmethod(flatten_and_or, op="disjunction")

    def negation(self, items):
        negated_formula = items[0]
        if negated_formula.data in ["negation", "negation_exc"]:
            doubly_negated = negated_formula.children[0]
            return doubly_negated
        return Tree("negation", items)

    negation_exc = negation

    def quantification(self, items, op: str):
        *variables, inner_formula = items
        if inner_formula.data == op:
            *additional_variables, doubly_quantified_formula = inner_formula.children
            return Tree(
                op, variables + additional_variables + [doubly_quantified_formula]
            )
        return Tree(op, items)

    universal_quantification = partialmethod(
        quantification, op="universal_quantification"
    )
    existential_quantification = partialmethod(
        quantification, op="existential_quantification"
    )


# axiom_text = """exists Y exists Z all X all U all UU exists T exists TT ((A(X) | -U(X) | K(X,Z)) & (B(X,Y) | -V(X,Y,Z)) & (C(Z)))."""
# axiomAST = prover9_parser.parse(axiom_text)
# flattener = AssociativeFlattener()
# flatAst = flattener.transform_repeatedly(axiomAST)
# treeExplainer(axiomAST)
# treeExplainer(flatAst)
# quit()
def test_free_variables_extraction():
    extractor = P9FreeVariablesExtractor()
    axiom_to_free_vars = [("(all Y p(X,Y)).", {"X"}),
                          ("(all Z all W l(X,Y,Z,W)).", {"X", "Y"})]
    for axiom, free_vars in axiom_to_free_vars:
        ast = prover9_parser.parse(axiom)
        assert free_vars == (actual:=extractor.transform(ast)), f"expected {free_vars}, got {actual}"
        assert free_vars == (actual:=extractor.transform(AssociativeFlattener().transform_repeatedly(ast))), f"expected {free_vars}, got {actual}"
    print("All good with free vars extraction")

class ReverseAssociativeFlattener(Transformer):
    """Inverts the operations of the associative flattener"""

    def __init__(self, visit_tokens=False):
        super().__init__(visit_tokens)

    def transform_repeatedly(self, tree):
        oldtree = tree
        newtree = self.transform(oldtree)
        while newtree != oldtree:
            oldtree = newtree
            newtree = self.transform(newtree)
        return newtree

    def de_flatten_and_or(self, items, op: str):
        if len(items) > 2:
            return Tree(op, [items[0], Tree(op, items[1:])])
        return Tree(op, items)
    conjunction = conjunction_exc = partialmethod(de_flatten_and_or, op="conjunction")
    disjunction = disjunction_exc = partialmethod(de_flatten_and_or, op="disjunction")

    def quantification(self, items, op: str):
        *variables, inner_formula = items
        #variables = sorted(variables) <- changes previous results too much
        if len(variables) > 1:
            return Tree(op, [variables[0], Tree(op, variables[1:] + [inner_formula])])
            
        return Tree(op, items)

    universal_quantification = partialmethod(
        quantification, op="universal_quantification"
    )
    existential_quantification = partialmethod(
        quantification, op="existential_quantification"
    )


# axiom_text = """exists Y exists Z all X all U all UU exists T exists TT ((A(X) | -U(X) | K(X,Z)) & (B(X,Y) | -V(X,Y,Z)) & (C(Z)))."""
# axiomAST = prover9_parser.parse(axiom_text)
# flatAst = AssociativeFlattener().transform_repeatedly(axiomAST)
# reverseflatAst = ReverseAssociativeFlattener().transform_repeatedly(axiomAST)
# treeExplainer(axiomAST)
# treeExplainer(flatAst)
# treeExplainer(reverseflatAst)
# assert reverseflatAst == axiomAST
# quit()


class TypeChecker(Interpreter):
    def __init__(self):
        self.axioms_signature = Signature()
        self.isUniversalRule = "maybe"

    # def equality_atom(self, items):
    #     return True
    # def predicate(self, items):
    #     return True
    def isUniversal(self, tree: Tree):
        self.isUniversalRule = True
        self.visit(tree)
        out = self.isUniversalRule
        self.isUniversalRule = "maybe"
        return out

    def conjunction(self, tree):
        left, right = tree.children
        if not (
            left.data in ["conjunction", "predicate", "equality_atom"]
            and right.data in ["conjunction", "predicate", "equality_atom"]
        ):
            print(f"auch at {tree.data}")
            self.isUniversalRule = False
        self.visit_children(tree)

    def universal_quantification(self, tree):
        variable, quantified_formula = tree.children
        if not (
            quantified_formula.data
            in [
                "entailment",
                "conjunction",
                "predicate",
                "equality_atom",
                "universal_quantification",
            ]
        ):
            print(f"auch at {tree.data}")
            self.isUniversalRule = False
        self.visit_children(tree)

    def must_not_appear(self, tree):
        print(f"auch at {tree.data}")
        self.isUniversalRule = False

    existential_quantification = must_not_appear

    disjunction = must_not_appear
    conjunction_exc = must_not_appear
    disjunction_exc = must_not_appear
    reverse_entailment = must_not_appear
    equivalence_entailment = must_not_appear
    entailment_exc = must_not_appear
    reverse_entailment_exc = must_not_appear
    equivalence_entailment_exc = must_not_appear
    negation = must_not_appear
    negation_exc = must_not_appear

    # car = lambda self, tree: tree.children[0]
    # start = car
    # lines = car
    # line = car
    # sentence = car
    # label = lambda self, items: None


# tc = TypeChecker()
# treeExplainer(ast1)
# print(tc.isUniversalRule)
# print(tc.isUniversal(ast1))
# print(tc.isUniversalRule)
# print(tc.isUniversal(ast2))
# print(tc.isUniversal(ast3))
# print(tc.isUniversal(ast4))
# print(tc.isUniversal(ast5))


def dual_quantifier(string):
    q_set = {"existential_quantification", "universal_quantification"}
    if not string in q_set:
        raise TypeError(f"Dual quantifier got {string}")
    return q_set.difference({string}).pop()


def dual_op(string):
    op_map = {
        "existential_quantification": "universal_quantification",
        "universal_quantification": "existential_quantification",
        "conjunction": "disjunction",
        "disjunction": "conjunction",
        "false": "true",
        "true": "false",
    }
    if not string in op_map.keys():
        raise TypeError(
            f"Operation should not be called to get dual. Operation was {string}"
        )
    return op_map[string]


class ReplaceVariable(Interpreter):
    """Replaces a variable with another. In the case of conflicting quantification the inner formula wins. E.g. calling replace X->X1 on (all X A(X)) will not change the formula, but calling it on (all X A(X)) & B(X) will result in (all X A(X)) & B(X1)"""

    def __init__(self, replaced: str, replacing: str):
        super().__init__()
        self.replaced = replaced
        self.replacing = replacing

    def __default__(self, tree):
        # These shenaningans are needed to force the behavior of an Interpretr into something more similar to a Transformer
        # if using a transformer this is not necessary, however, branching logic is needed to skip inner conflicting formulas. Therefore an Interpreter must be used. But interpreters, by default, do not visit non-Tree nodes
        if isinstance(tree, Tree):
            return Tree(tree.data, self.visit_children(tree))
        elif isinstance(tree, Token) and tree.type == "VARIABLE":
            return self.VARIABLE(tree)
        else:
            return tree
        
    def visit_children(self, tree):
        # if using a transformer this is not necessary, however, branching logic is needed to skip inner conflicting formulas. Therefore an Interpreter must be used. But interpreters, by default, do not visit non-Tree nodes
        return [self._visit_tree(child) if isinstance(child, Tree) else self.VARIABLE(child) if isinstance(child, Token) and child.type == "VARIABLE" else child for child in tree.children]
    def transform(self, tree):
        return self.visit(tree)
    
    def VARIABLE(self, token):
        assert isinstance(token, Token)
        if token.value == self.replaced:
            return Token("VARIABLE", self.replacing) # value.replace(self.replaced, self.replacing) <- this is wrong because it replaces substrings within variable names
        return token 
    
    def quantification(self, tree, quantification_type):
        quantified_variable, *bounding_formula_list, inner_formula = tree.children
        if str(quantified_variable) == self.replaced: 
            # conflicting quantification: the inner formula wins
            return tree
        else:
            # no conflict: the replacement proceeds on
            return Tree(tree.data, self.visit_children(tree)) if isinstance(tree, Tree) else self.visit(tree)

    universal_quantification = partialmethod(
        quantification, quantification_type="universal_quantification"
    )
    existential_quantification = partialmethod(
        quantification, quantification_type="existential_quantification"
    )
    universal_quantification_bounded = partialmethod(
        quantification, quantification_type="universal_quantification_bounded"
    )
    existential_quantification_bounded = partialmethod(
        quantification, quantification_type="existential_quantification_bounded"
    )

# rp = ReplaceVariable("X", "X1")
# # treeExplainer(rp.transform(ast1))
# treeExplainer(rp.transform(prover9_parser.parse("(A(X,Y,Z) | U(X,C)).")))
# treeExplainer(rp.transform(prover9_parser.parse("(all X A(X)).")))
# treeExplainerRED(rp.visit(prover9_parser.parse("((all X A(X)) & B(X)).")))
# exit()

class ToUniqueVariables(Transformer):
    """Each quantified variable will have a unique name. Also redundant quantifications will be removed. Not to be used with flattened formulas!"""

    def __init__(self, visit_tokens=True):
        super().__init__(visit_tokens)
        self.quantified_variables = set()

    def adjust_variables(self, tree):
        self.quantified_variables = set()
        out_tree = self.transform(tree)
        self.quantified_variables = set()
        return out_tree

    def quantification(self, items, quantification_type):
        quantified_variable, *bounding_formula_list, inner_formula = items
        if str(quantified_variable) not in P9FreeVariablesExtractor().transform(inner_formula):
            return inner_formula
        if str(quantified_variable) in self.quantified_variables:
            match = re.match(r"([a-zA-Z]+)(.*?)(\d+)", str(quantified_variable))
            if not match: 
                root = str(quantified_variable)
                new_number = 1
            else:
                root, _, number = match.groups()
                new_number = int(number) + 1
            while root+str(new_number) in self.quantified_variables:
                new_number += 1
            new_name = root+str(new_number) #str(quantified_variable) + str(len(self.quantified_variables))
            self.quantified_variables.add(new_name)
            rp = ReplaceVariable(str(quantified_variable), new_name)
            replacing_inner_formula = rp.transform(inner_formula)
            if bounding_formula_list != []:
                bounding_formula_list = [rp.transform(bounding_formula_list[0])]
            return Tree(
                quantification_type,
                [Token(type_="VARIABLE", value=new_name)]
                + bounding_formula_list
                + [replacing_inner_formula],
            )
        self.quantified_variables.add(str(quantified_variable))
        return Tree(quantification_type, items)

    universal_quantification = partialmethod(
        quantification, quantification_type="universal_quantification"
    )
    existential_quantification = partialmethod(
        quantification, quantification_type="existential_quantification"
    )
    universal_quantification_bounded = partialmethod(
        quantification, quantification_type="universal_quantification_bounded"
    )
    existential_quantification_bounded = partialmethod(
        quantification, quantification_type="existential_quantification_bounded"
    )


def test_variables_adjuster():
    unique = ToUniqueVariables()
    toString = ToString()
    in_outs = [("((all X A(X,Y)) & (exists X P(X)) & (exists X V(X))).", "((all X A(X,Y)) & (exists X1 P(X1)) & (exists X2 V(X2)))."),
               ("((all X A(X,Y)) & (exists X P(X)) & (exists X (V(X) & all X B(X)))).", "((all X A(X,Y)) & (exists X1 P(X1)) & (exists X3 (V(X3) & all X2 B(X2))))."),
               ("all A all B all C all T all T2  ((((properContinuantPartOf(A,B,T)) & (properContinuantPartOf(B,C,T2)) & (temporalPartOf(T,T2)))) -> (properContinuantPartOf(A,C,T))) # label(\"proper-continuant-part-of-transitive-at-a-time\").", 
                "all A all B all C all T all T2  ((((properContinuantPartOf(A,B,T)) & (properContinuantPartOf(B,C,T2)) & (temporalPartOf(T,T2)))) -> (properContinuantPartOf(A,C,T))) # label(\"proper-continuant-part-of-transitive-at-a-time\").")
               ]
    for inp, out in in_outs:
        base = prover9_parser.parse(inp)
        calc = unique.adjust_variables(base)
        ground = prover9_parser.parse(out)
        assert calc == ground, f"From black/white and string should have got green, got read instead {base, treeExplainer(base), treeExplainerGREEN(ground), treeExplainerRED(calc)}"
    print("All good for variables adjuster")

class ToPrenex(Transformer):
    """Transform a formula in prenex normal form"""

    def __init__(self, visit_tokens=True):
        super().__init__(visit_tokens)

    def adjust_transform_repeatedly(self, tree):
        unique = ToUniqueVariables()
        adjusted_tree = unique.adjust_variables(tree)
        oldtree = adjusted_tree
        newtree = unique.adjust_variables(self.transform(adjusted_tree))
        while newtree != oldtree:
            oldtree = newtree
            newtree = unique.adjust_variables(self.transform(oldtree))
        return newtree

    def entailment(self, children):
        left, right = children
        if right.data in [
            "existential_quantification",
            "universal_quantification",
        ] and not left.data in [
            "existential_quantification",
            "universal_quantification",
        ]:
            quantified_variable, quantified_formula = right.children
            return Tree(
                right.data,
                [quantified_variable, Tree("entailment", [left, quantified_formula])],
            )
        if left.data in [
            "existential_quantification",
            "universal_quantification",
        ] and not right.data in [
            "existential_quantification",
            "universal_quantification",
        ]:
            quantified_variable, quantified_formula = left.children
            return Tree(
                dual_quantifier(left.data),
                [quantified_variable, Tree("entailment", [quantified_formula, right])],
            )
        if left.data in [
            "existential_quantification",
            "universal_quantification",
        ] and right.data in ["existential_quantification", "universal_quantification"]:
            left_quantified_variable, left_quantified_formula = left.children
            right_quantified_variable, right_quantified_formula = right.children
            return Tree(
                dual_quantifier(left.data),
                [
                    left_quantified_variable,
                    Tree(
                        right.data,
                        [
                            right_quantified_variable,
                            Tree(
                                "entailment",
                                [left_quantified_formula, right_quantified_formula],
                            ),
                        ],
                    ),
                ],
            )
        return Tree("entailment", children)

    entailment_exc = entailment

    def reverse_entailment(self, children):
        left, right = children
        return self.entailment([right, left])

    equivalence_entailment_exc = reverse_entailment

    def symmetric_op(self, children, operator: str):
        left, right = children
        if right.data in [
            "existential_quantification",
            "universal_quantification",
        ] and not left.data in [
            "existential_quantification",
            "universal_quantification",
        ]:
            quantified_variable, quantified_formula = right.children
            return Tree(
                right.data,
                [quantified_variable, Tree(operator, [left, quantified_formula])],
            )
        if left.data in [
            "existential_quantification",
            "universal_quantification",
        ] and not right.data in [
            "existential_quantification",
            "universal_quantification",
        ]:
            quantified_variable, quantified_formula = left.children
            return Tree(
                left.data,
                [quantified_variable, Tree(operator, [quantified_formula, right])],
            )
        if (
            left.data == "universal_quantification"
            and right.data == left.data
            and operator == "conjunction"
        ):
            # (all X phi(X)) & (all Y psi(Y)) ---> all X (phi(X) & psi(X))
            left_quantified_variable, left_quantified_formula = left.children
            right_quantified_variable, right_quantified_formula = right.children
            replace = ReplaceVariable(
                replaced=right_quantified_variable, replacing=left_quantified_variable
            )
            replaced_right_quantified_formula = replace.transform(
                right_quantified_formula
            )
            return Tree(
                left.data,
                [
                    left_quantified_variable,
                    Tree(
                        "conjunction",
                        [left_quantified_formula, replaced_right_quantified_formula],
                    ),
                ],
            )
        if (
            left.data == "existential_quantification"
            and right.data == left.data
            and operator == "disjunction"
        ):
            # (exists X phi(X)) | (exists Y psi(Y)) ---> exists X (phi(X) | psi(X))
            left_quantified_variable, left_quantified_formula = left.children
            right_quantified_variable, right_quantified_formula = right.children
            replace = ReplaceVariable(
                replaced=right_quantified_variable, replacing=left_quantified_variable
            )
            replaced_right_quantified_formula = replace.transform(
                right_quantified_formula
            )
            return Tree(
                left.data,
                [
                    left_quantified_variable,
                    Tree(
                        "disjunction",
                        [left_quantified_formula, replaced_right_quantified_formula],
                    ),
                ],
            )
        if left.data in [
            "existential_quantification",
            "universal_quantification",
        ] and right.data in ["existential_quantification", "universal_quantification"]:
            left_quantified_variable, left_quantified_formula = left.children
            right_quantified_variable, right_quantified_formula = right.children
            return Tree(
                left.data,
                [
                    left_quantified_variable,
                    Tree(
                        right.data,
                        [
                            right_quantified_variable,
                            Tree(
                                operator,
                                [left_quantified_formula, right_quantified_formula],
                            ),
                        ],
                    ),
                ],
            )
        return Tree(operator, children)

    # disjunction = partial(binary_op, operator = "disjunction")
    def disjunction(self, children):
        return self.symmetric_op(children, "disjunction")

    disjunction_exc = disjunction

    # conjunction = partial(binary_op, operator = "conjunction")
    def conjunction(self, children):
        return self.symmetric_op(children, "conjunction")

    conjunction_exc = conjunction

    def equivalence_entailment(self, children):
        left, right = children
        return Tree(
            "conjunction",
            [Tree("entailment", [left, right]), Tree("entailment", [right, left])],
        )
        # return self.conjunction([self.entailment([left, right]), self.entailment([right, left])])

    equivalence_entailment_exc = equivalence_entailment

    def negation_exc(self, children):
        negated_formula = children[0]
        if negated_formula.data in [
            "existential_quantification",
            "universal_quantification",
        ]:
            quantified_variable, quantified_formula = negated_formula.children
            return Tree(
                dual_quantifier(negated_formula.data),
                [quantified_variable, Tree("negation", [quantified_formula])],
            )
        return Tree("negation", children)

    negation = negation_exc

    # do_nothing = lambda self, items: items
    # car = lambda self, items: items[0]
    # start = car
    # lines = car
    # line = car
    # sentence = car

    # label = lambda self, items: None


# tp=ToPrenex()
# textp = 'all X (exists Y R(X,Y)) & (exists Z P(X,Z)).'
# textp = '((all X (exists Y R(X,Y))) & (all X(exists Z P(X,Z)))).'
# textp = '((exists X (all Y R(X,Y))) | (exists X (all Z P(X,Z)))).'
# textp = '((all X (exists Y R(X,Y))) | (all X(exists Z P(X,Z)))).'
# astp=prover9_parser.parse(textp)
# treeExplainer(astp)
# treeExplainer(tp.adjust_transform_repeatedly(astp))
# quit()

# treeExplainer(ast0)
# ast00 = tp.adjust_transform_repeatedly(ast0)
# treeExplainer(ast00)
# treeExplainer(ast1)
# ast11 = tp.adjust_transform_repeatedly(ast1)
# treeExplainer(ast11)
# treeExplainer(ast2)
# ast22 = tp.adjust_transform_repeatedly(ast2)
# treeExplainer(ast22)
# treeExplainer(ast3)
# ast33 = tp.adjust_transform_repeatedly(ast3)
# treeExplainer(ast33)
# treeExplainer(ast4)
# ast44 = tp.transform(ast4)
# treeExplainer(ast44)
# treeExplainer(ast5)
# ast55 = tp.transform(ast5)
# treeExplainer(ast55)
# s()


class ToConjunctiveNormalForm(Interpreter):
    """Transform a propositional formula in conjunctive normal form. Non propositional operators are ignored"""

    # def __init__(self, visit_tokens = True):
    #     super().__init__(visit_tokens)

    def visit_repeatedly(self, tree):
        oldtree = tree
        newtree = self.visit(oldtree)
        while newtree != oldtree:
            oldtree = newtree
            newtree = self.visit(oldtree)
        return newtree

    def entailment(self, tree):
        left, right = tree.children
        return Tree(
            "disjunction", [Tree("negation", [self.visit(left)]), self.visit(right)]
        )

    entailment_exc = entailment

    def reverse_entailment(self, tree):
        left, right = tree.children
        return self.entailment([right, left])

    equivalence_entailment_exc = reverse_entailment

    def disjunction(self, tree):
        left, right = tree.children
        if right.data == "conjunction":
            sub_left, sub_right = right.children
            return Tree(
                "conjunction",
                [
                    Tree("disjunction", [self.visit(left), self.visit(sub_left)]),
                    Tree("disjunction", [self.visit(left), self.visit(sub_right)]),
                ],
            )
        if left.data == "conjunction":
            sub_left, sub_right = left.children
            return Tree(
                "conjunction",
                [
                    Tree("disjunction", [self.visit(right), self.visit(sub_left)]),
                    Tree("disjunction", [self.visit(right), self.visit(sub_right)]),
                ],
            )
        return Tree("disjunction", self.visit_children(tree))

    disjunction_exc = disjunction

    def equivalence_entailment(self, tree):
        left, right = tree.children
        return Tree(
            "conjunction",
            [
                Tree("entailment", [self.visit(left), self.visit(right)]),
                Tree("entailment", [self.visit(right), self.visit(left)]),
            ],
        )

    equivalence_entailment_exc = equivalence_entailment

    def false(self, tree):
        return Tree("false", [])

    def true(self, tree):
        return Tree("true", [])

    def negation(self, tree):
        negated_formula = tree.children[0]
        if negated_formula.data in ["disjunction", "conjunction"]:
            left, right = negated_formula.children
            return Tree(
                dual_op(negated_formula.data),
                [
                    Tree("negation", [self.visit(left)]),
                    Tree("negation", [self.visit(right)]),
                ],
            )
        if negated_formula.data in ["negation", "negation_exc"]:
            sub_negated_formula = negated_formula.children[0]
            return self.visit(sub_negated_formula)
        if negated_formula.data in ["true", "false"]:
            return Tree(dual_op(negated_formula.data), [])
        return Tree("negation", self.visit_children(tree))

    negation_exc = negation

    def pass_par_rule(self, tree, par: str):
        return Tree(Token("RULE", par), self.visit_children(tree))

    def pass_par(self, tree, par: str):
        return Tree(par, self.visit_children(tree))

    def terminate(self, tree):
        return tree

    start = partialmethod(pass_par_rule, par="start")
    lines = partialmethod(pass_par_rule, par="lines")
    line = partialmethod(pass_par_rule, par="line")
    conjunction = partialmethod(pass_par, par="conjunction")
    universal_quantification = partialmethod(pass_par, par="universal_quantification")
    existential_quantification = partialmethod(
        pass_par, par="existential_quantification"
    )
    universal_quantification_bounded = partialmethod(
        pass_par, par="universal_quantification_bounded"
    )
    existential_quantification_bounded = partialmethod(
        pass_par, par="existential_quantification_bounded"
    )
    # def universal_quantification(self, tree):
    #     return Tree("universal_quantification", [])
    predicate = terminate
    equality_atom = terminate
    dom = terminate
    cond = terminate
    empty = terminate
    VARIABLE = terminate
    # start = proceeds #pass_car
    # lines = proceeds #pass_by
    # line = proceeds #visit_self


class ToPrenexCNF:
    """Transform a formula in prenex conjunctive normal form."""

    def __init__(self):
        self.toPrenex = ToPrenex()
        self.toCNF = ToConjunctiveNormalForm()

    def transform_repeatedly(self, tree):
        oldtree = tree
        newtree_pre = self.toPrenex.adjust_transform_repeatedly(oldtree)
        newtree = self.toCNF.visit_repeatedly(newtree_pre)
        while newtree != oldtree:
            oldtree = newtree
            newtree_pre = self.toPrenex.adjust_transform_repeatedly(oldtree)
            newtree = self.toCNF.visit_repeatedly(newtree_pre)
        return newtree


# toCNF = ToConjunctiveNormalForm()
# toPCNF = ToPrenexCNF()
# text = "(P(x,y) & Q(a,b) & C(z) -> R(a))."
# text = "((P(x,y) & Q(a,b)) | (C(z) & R(a)))."
# text = "((P(x,y) & Q(a,b)) | (C(z)) )."
# text = "(- (((P(x,y) & -Q(a,b)) | (C(z)))) )."
# text = "((P(x,y) & Q(a,b)) | (C(z) <-> R(a)))."
# text = "(all X p(X) & - (exists Y (q(X,Y))))."
# text = "(all X p(X) & - (exists Y (q(X,Y))))."
# text = '(all X all Y all Z all T all T2 A(X,Y,T) & A(Y,Z,T2) & B(T,T2) -> A(X,Z,T)).'
# text = '(all X all Y all Z all T (A(X,Y,T) & (exists T2 (A(Y,Z,T2) & B(T,T2))) -> A(X,Z,T))).'
# ast = prover9_parser.parse(text)
# treeExplainer(ast)
# cnfTree = toCNF.visit_repeatedly(ast)
# pcnfTree = toPCNF.transform_repeatedly(ast)
# treeExplainer(cnfTree)
# treeExplainer(pcnfTree)
# quit()


class ToReversePrenexCNF(Transformer):
    """Transform a formula in prenex CNF and transforms it in reverse prenex CNF normal form (push quantifiers in the innermost position possible -- if it is immediate to do so)
    If the formula is not prenex CNF it will be made so before starting"""

    def __init__(self, visit_tokens=True):
        super().__init__(visit_tokens)
        self.freeVars = P9FreeVariablesExtractor()
        self.toPCNF = ToPrenexCNF()
        self.stringer = ToString()
        self.unique = ToUniqueVariables()
        self.commutes = {
            "existential_quantification": "disjunction",
            "universal_quantification": "conjunction",
        }

    def adjust_transform_repeatedly(self, tree):
        # ensures the tree is PCNF
        PCNFtree = self.toPCNF.transform_repeatedly(tree)
        if PCNFtree != tree:
            my_logger.debug(f"As an input of ToReversePrenexCNF I got a formula not in PCNF. Precisely {self.stringer.visit(tree)}. I have transformed it in PCNF: the formula is now {self.stringer.visit(PCNFtree)}.")

        adjusted_tree = self.unique.adjust_variables(PCNFtree)
        oldtree = adjusted_tree
        newtree = self.unique.adjust_variables(self.transform(adjusted_tree))
        while newtree != oldtree:
            # print("I am transforming an additional time")
            oldtree = newtree
            newtree = self.unique.adjust_variables(self.transform(oldtree))
        return newtree

    def quantification(self, children, quantification_type: str):
        quantified_variable, quantified_formula = children
        if quantified_formula.data in ["negation", "negation_exc"]:
            negated_formula = quantified_formula.children[0]
            return Tree(
                "negation",
                [
                    Tree(
                        dual_quantifier(quantification_type),
                        [quantified_variable, negated_formula],
                    )
                ],
            )
        if quantified_formula.data in BINARY_OPS:
            left, right = quantified_formula.children
            if not quantified_variable in self.freeVars.transform(
                left
            ) and not quantified_variable in self.freeVars.transform(right):
                raise TypeError(
                    f"In quantified formula {quantified_formula} the quantified variable {quantified_variable} does not occurr! This should never happen."
                )
            if not quantified_variable in self.freeVars.transform(left):
                return Tree(
                    quantified_formula.data,
                    [left, Tree(quantification_type, [quantified_variable, right])],
                )
            if not quantified_variable in self.freeVars.transform(right):
                return Tree(
                    quantified_formula.data,
                    [Tree(quantification_type, [quantified_variable, left]), right],
                )
        if quantified_formula.data == self.commutes[quantification_type]:
            left, right = quantified_formula.children
            return Tree(
                quantified_formula.data,
                [
                    Tree(quantification_type, [quantified_variable, left]),
                    Tree(quantification_type, [quantified_variable, right]),
                ],
            )
        return Tree(quantification_type, [quantified_variable, quantified_formula])

    existential_quantification = partialmethod(
        quantification, quantification_type="existential_quantification"
    )
    universal_quantification = partialmethod(
        quantification, quantification_type="universal_quantification"
    )

    def negation_exc(self, children):
        negated_formula = children[0]
        if negated_formula.data in ["negation", "negation_exc"]:
            doubly_negated_formula = negated_formula.children[0]
            return doubly_negated_formula
        return Tree("negation", children)

    negation = negation_exc


# tp=ToReversePrenexCNF()
# textp = '(all X -( A(X) | False)).'
# textp = 'all X (exists Y R(X,Y)) & (exists Z P(X,Z)).'
# textp = '((all X (exists Y R(X,Y))) & (all X(exists Z P(X,Z)))).'
# textp = '((exists X (all Y R(X,Y))) | (exists X (all Z P(X,Z)))).'
# textp = '((all X (exists Y R(X,Y))) | (all X(exists Z P(X,Z)))).'
# textp = '(all X exists Y (R(X,Y) | P(X,Z))).'
# textp = '(exists X - all Y (R(X,Y) |  P(X,Z))).'
# textp = '(all X all Y (R(X,Y) | P(Y))).'
# textp = "(all X all Y all Z all T all TAU cP(X,Y,T) & cP(Y,Z,TAU) & tP(T,TAU) -> cP(X,Z,T))."
# astp=prover9_parser.parse(textp)
# treeExplainerGREEN(astp)
# print(astp)
# # treeExplainer(ToPrenex().adjust_transform_repeatedly(astp))
# treeExplainerRED(tp.adjust_transform_repeatedly(astp))
# exit()

class ToMiniscopedCNF(Transformer):
    """Transform a formula in prenex CNF and transforms it in reverse prenex CNF normal form (push quantifiers in the innermost position possible -- if it is immediate to do so)
    If the formula is not prenex CNF it will be made so before starting"""

    def __init__(self, visit_tokens=True):
        super().__init__(visit_tokens)
        self.freeVars = P9FreeVariablesExtractor()
        self.toPCNF = ToPrenexCNF()
        self.commutes = {
            "existential_quantification": "disjunction",
            "universal_quantification": "conjunction",
        }
        self.unique = ToUniqueVariables()
        self.flattener = AssociativeFlattener()
        self.reverse_flattener = ReverseAssociativeFlattener()

    def adjust_transform_repeatedly(self, tree):
        # ensures the tree is PCNF
        PCNFtree = self.toPCNF.transform_repeatedly(tree)
        # ensures variable name uniqueness
        UniquePNCFtree = self.unique.adjust_variables(PCNFtree)
        # ensures the tree is associatively-flattened
        FlatUniquePNCFtree = self.flattener.transform_repeatedly(UniquePNCFtree)
        oldtree = FlatUniquePNCFtree
        # newtree = self.unique.adjust_variables(self.transform(oldtree))
        # newtree = self.transform(oldtree)
        newtree = self.flattener.transform_repeatedly(self.transform(oldtree))
        while newtree != oldtree:
            oldtree = newtree
            # newtree = self.unique.adjust_variables(self.transform(oldtree))
            # newtree = self.transform(oldtree)
            newtree = self.flattener.transform_repeatedly(self.transform(oldtree))
        return self.unique.adjust_variables(self.reverse_flattener.transform_repeatedly(newtree))

    def quantification(self, children, quantification_type: str):
        *quantified_variables, quantified_formula = children

        if quantified_formula.data in ["negation", "negation_exc"]:
            negated_formula = quantified_formula.children[0]
            return Tree(
                "negation",
                [
                    Tree(
                        dual_quantifier(quantification_type),
                        quantified_variables +[negated_formula],
                    )
                ],
            )
            
        if quantified_formula.data in BINARY_OPS:
            def get_candidate_variables_for_splitting(quantified_variables, quantified_formula):
                """If None is returned there are no candidates for splitting"""
                if len(quantified_variables) < 2: return None 
                variable_sets = [frozenset(self.freeVars.transform(child)) for child in quantified_formula.children]
                variable_to_containing_sets = {var: {var_set for var_set in variable_sets if var in var_set} for var in quantified_variables}

                candidates = set()
                for var1 in quantified_variables:
                    for var2 in frozenset(quantified_variables).difference(frozenset.union(*variable_to_containing_sets[var1])):
                        candidates.add(frozenset({var1,var2}))             
                if len(candidates) > 0:
                    # for now a random (not random, but meaninglessy ordered for reproducibility) couple of candidate variables is returned
                    var1, var2 = tuple(sorted(list(candidates))[0])
                    # order the variables in fix order for reproducibility
                    if str(var1) > str(var2):
                        temp = var1
                        var1 = var2
                        var2 = temp
                    return var1, var2
                else:
                    return None
            
            candidates = get_candidate_variables_for_splitting(quantified_variables, quantified_formula)
            if candidates:
                var1, var2 = candidates
                remaining_variables = [var for var in quantified_variables if var not in [var1, var2]]
                children1 = [child for child in quantified_formula.children if var1 in self.freeVars.transform(child)]
                children2 = [child for child in quantified_formula.children if var2 in self.freeVars.transform(child)]
                if len(children1) + len(children2) > len(quantified_formula.children): raise TypeError(f"The variables {var1}, {var2} do not split the set {quantified_variables}! Something went wrong during the splitting calculation")
                if 0 in [len(children1),len(children2)]: raise TypeError(f"Either of variables {var1}, {var2} does not appear in the formula {quantified_formula}! This should not happen.")
                remaining_children = [child for child in quantified_formula.children if (child not in children1) and (child not in children2)]
                if len(remaining_variables) == 0:
                    if len(remaining_children) == 0:
                        return Tree(
                            quantified_formula.data,
                            [Tree(quantification_type, [var1, (Tree(quantified_formula.data, children1) if len(children1) > 1 else children1[0])]), 
                             Tree(quantification_type, [var2, (Tree(quantified_formula.data, children2) if len(children2) > 1 else children2[0])])],
                        )
                    if len(remaining_children) > 0:
                        # raise TypeError("The variables do not exhaust the children but there are no other variables!") # <- can happen if there is a child with no variables
                        return Tree(
                            quantified_formula.data,
                            remaining_children + [Tree(quantification_type, [var1, (Tree(quantified_formula.data, children1) if len(children1) > 1 else children1[0])]), Tree(quantification_type, [var2, (Tree(quantified_formula.data, children2) if len(children2) > 1 else children2[0])])],
                        )
                         
                if len(remaining_variables) > 0:
                    if len(remaining_children) == 0:
                        return Tree(quantification_type, remaining_variables + [Tree(
                            quantified_formula.data,
                            [Tree(quantification_type, [var1, (Tree(quantified_formula.data, children1) if len(children1) > 1 else children1[0])]), Tree(quantification_type, [var2, (Tree(quantified_formula.data, children2) if len(children2) > 1 else children2[0])])],
                        )])
                    if len(remaining_children) > 0:
                        return Tree(quantification_type, remaining_variables + [Tree(
                            quantified_formula.data,
                            remaining_children + [Tree(quantification_type, [var1, (Tree(quantified_formula.data, children1) if len(children1) > 1 else children1[0])]), Tree(quantification_type, [var2, (Tree(quantified_formula.data, children2) if len(children2) > 1 else children2[0])])],
                        )])
            else:
                variable_appearing_less = sorted([(var,len([child for child in quantified_formula.children if var in self.freeVars.transform(child)])) for var in quantified_variables], key= lambda x:x[1])[0][0]

                children_less = [child for child in quantified_formula.children if variable_appearing_less in self.freeVars.transform(child)]
                remaining_variables = [var for var in quantified_variables if var != variable_appearing_less]
                remaining_children = [child for child in quantified_formula.children if child not in children_less]
                assert len(children_less) + len(remaining_children) == len(quantified_formula.children)
                if len(remaining_children) == 0:
                    pass # This case is skipped here since if the tree arrives at the end of this function it will returned alredy 
                    # return Tree(quantification_type,
                    #     quantified_variables + [quantified_formula])
                if len(remaining_children) > 0:
                    if len(remaining_variables) == 0:
                        return Tree(quantified_formula.data, remaining_children + [Tree(quantification_type, [variable_appearing_less] + (children_less if len(children_less) == 1 else [Tree(quantified_formula.data, children_less)]))])
                    if len(remaining_variables) > 0:
                        return Tree(quantification_type, 
                            remaining_variables + [Tree(quantified_formula.data, remaining_children + [Tree(quantification_type, [variable_appearing_less] + (children_less if len(children_less) == 1 else [Tree(quantified_formula.data, children_less)]))])]
                        )
                     
        if quantified_formula.data == self.commutes[quantification_type]:
            return Tree(
                quantified_formula.data,
                [Tree(quantification_type, quantified_variables + [child]) for child in quantified_formula.children],
            )
        return Tree(quantification_type, quantified_variables + [quantified_formula])

    existential_quantification = partialmethod(
        quantification, quantification_type="existential_quantification"
    )
    universal_quantification = partialmethod(
        quantification, quantification_type="universal_quantification"
    )

    def negation_exc(self, children):
        negated_formula = children[0]
        if negated_formula.data in ["negation", "negation_exc"]:
            doubly_negated_formula = negated_formula.children[0]
            return doubly_negated_formula
        return Tree("negation", children)

    negation = negation_exc



def test_miniscoping():    
    tp=ToMiniscopedCNF()
    textp = 'all X (exists Y R(X,Y)) & (exists Z P(X,Z)).'
    textp = '((all X (exists Y R(X,Y))) & (all X(exists Z P(X,Z)))).'
    textp = '((exists X (all Y R(X,Y))) | (exists X (all Z P(X,Z)))).'
    textp = '((all X (exists Y R(X,Y))) | (all X(exists Z P(X,Z)))).'
    textp = '(all X exists Y (R(X,Y) | P(X,Z))).'
    textp = '(exists X - all Y (R(X,Y) |  P(X,Z))).'

    tests = [("(all X all Y all Z all T all TAU cP(X,Y,T) & cP(Y,Z,TAU) & tP(T,TAU) -> cP(X,Z,T)).","(all Y (all Z (all T ((all TAU ((-(cP(Y,Z,TAU))) | (-(tP(T,TAU))))) | (all X ((-(cP(X,Y,T))) | cP(X,Z,T)))))))."),
            ("(all X all Y (C(Y) & (A(X) | B(X,Y)))).","((all Y (C(Y))) & (all X (A(X) | (all Y1 (B(X,Y1))))))."),
            ("(all X all Y A(X) & B(X,Y)).","((all X (A(X))) & (all X1 (all Y (B(X1,Y)))))."),
            ("(all X all Y (A(X) | B(X,Y))).","(all X (A(X) | (all Y (B(X,Y)))))."),
            ("(all Y (C(Y) | (A(X) | B(X,Y)))).","(A(X) | (all Y (C(Y) | B(X,Y))))."),
            ("(all X -( A(X) | False)).","((True) & (-(exists X (A(X)))))."),
            ("(all X all Y (C(Y) | (A(X) & B(X,Y)))).", "(((all X (A(X))) | (all Y (C(Y)))) & (all Y1 (C(Y1) | (all X1 (B(X1,Y1))))))."),
            ("(all X all Y (C(Y) & (A(X) | B(X,Y)))).","((all Y (C(Y))) & (all X (A(X) | (all Y1 (B(X,Y1))))))."),
            ]
    for test in tests:
        miniscoped = ToMiniscopedCNF().adjust_transform_repeatedly(prover9_parser.parse(test[0]))
        ground = prover9_parser.parse(test[1])
        assert miniscoped == ground, [treeExplainerRED(miniscoped), treeExplainerGREEN(ground)]
        
    textp = '(all X all Y (R(X,Y) | P(Y))).'
    astp=prover9_parser.parse(textp)
    treeExplainerGREEN(astp)
    treeExplainer(ToReversePrenexCNF().adjust_transform_repeatedly(astp))
    treeExplainerRED(tp.adjust_transform_repeatedly(astp))
    print(ToString().visit(tp.adjust_transform_repeatedly(astp)))




def test_to_string():
    tos = ToString()
    # text = '(all X all Y all Z all T (A(X,Y,T) & (exists T2 (A(Y,Z,T2) & B(T,T2))) -> A(X,Z,T))).'
    # ast = prover9_parser.parse(text)
    # treeExplainer(ast)
    # string = tos.visit(ast)
    # treeExplainerRED(Tree('universal_quantification', [Token('VARIABLE', 'X'), Tree('universal_quantification_bounded', [Token('VARIABLE', 'Y'), Tree('predicate', [Token('PREDICATE_SYMBOL', 'lec'), Token('VARIABLE', 'Y')]), Tree('disjunction', [Tree('negation', [Tree(Token('RULE', 'predicate'), [Token('PREDICATE_SYMBOL', 'lec'), Token('VARIABLE', 'Y')])]), Tree(Token('RULE', 'predicate'), [Token('PREDICATE_SYMBOL', 'att'), Token('VARIABLE', 'X'), Token('VARIABLE', 'Y')])])])]))
    string = tos.visit(
        Tree(
            "universal_quantification",
            [
                Token("VARIABLE", "X"),
                Tree(
                    "universal_quantification_bounded",
                    [
                        Token("VARIABLE", "Y"),
                        Tree(
                            "predicate",
                            [Token("PREDICATE_SYMBOL", "lec"), Token("VARIABLE", "Y")],
                        ),
                        Tree(
                            "disjunction",
                            [
                                Tree(
                                    "negation",
                                    [
                                        Tree(
                                            Token("RULE", "predicate"),
                                            [
                                                Token("PREDICATE_SYMBOL", "lec"),
                                                Token("VARIABLE", "Y"),
                                            ],
                                        )
                                    ],
                                ),
                                Tree(
                                    Token("RULE", "predicate"),
                                    [
                                        Token("PREDICATE_SYMBOL", "att"),
                                        Token("VARIABLE", "X"),
                                        Token("VARIABLE", "Y"),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
    )
    # string = tos.visit(Tree("predicate", [Token('PREDICATE_SYMBOL', 'lec'), Token('VARIABLE', 'Y')]))
    print(string)


class RemoveLines(Transformer):
    """removes start, lines, and line nodes; and also labels. Works only if the tree starts with one start, then one lines, then one single line"""

    def start(self, children):
        assert children[0].data == "lines"
        lines = children[0]
        assert len(lines.children) == 1
        assert lines.children[0].data == "line"
        line = lines.children[0]
        return (axiom := line.children[0])
class RemoveLabels(Transformer):
    """removes labels."""
    def label(self, children):
        return Discard
    
def test_remove_labels():
    text = "all A (B(A)) # label(\"proper-continuant-part-of-transitive-at-a-time\") ."
    ast = prover9_parser.parse(text)
    tast = RemoveLabels().transform(ast)
    treeExplainerGREEN(ast)
    treeExplainerRED(tast)

def get_existential_closure(tree: Tree, exceptions={}) -> Tree:
    free_vars: set[str] = (
        P9FreeVariablesExtractor().extract_free_variables_and_signature(tree)[0]
    )
    vars_to_close = free_vars.difference(exceptions)
    closed_tree = tree.copy()
    for var in sorted(list(vars_to_close)): # order for reproducibility
        closed_tree = Tree("existential_quantification", [var, closed_tree])
    return closed_tree
