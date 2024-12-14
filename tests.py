from check import P9FreeVariablesExtractor, P9Evaluator, P9Explainer, P9ModelReader, prover9_parser
from lark import Tree

def tests():
        print("Doing some tests...")

        # model_texts_axioms_evals = []

        # model_texts_axioms_evals.append(("""(P(c1,c2,c3,c4) & U(u,v) & Z(v)) # label(model).
                    # cc = ccc .""","all X all Y U(X,Y).",[False]))

        # model_text = """c1 = c2 .
        #                 cc = ccc ."""
        # axiom_text = "(all X all Y ((p(X,Y) & p(Y,X)) -> ((X)=(Y)))) # label(parthood_antysymmetry_Ad6)."
        # model_texts_axioms_evals.append((model_text, axiom_text, [False]))

        # model_text = """(P(c1,c2,c3,c4) & U(u,v) & Z(v)) # label(model).
        #                 A(x) ."""
        # axiom_text = "(exists X exists Y exists Z exists W P(X,Y,Z,W)."
        # model_texts_axioms_evals.append((model_text, axiom_text, [True]))

        model_texts_axioms_evals = [
            ("A(x).A(y).A(z).A(v).",
            "all X exists Y A(X,Y) & B(Y).",
            [False]),
            
            ("""A(x).A(y).A(z).A(zz).A(v).B(v).""",
            "all X exists Y A(X,Y) & B(Y).",
            [False]),

            ("""A(v).B(v).C(x).""",
            "exists Y A(Y) & B(Y).",
            [True]),
            
            ("""A(v).B(v).C(x).""",
            "all Y A(Y) & B(Y).",
            [False]),

            ("""A(v).B(v).C(x).""",
            """exists Y A(Y) & B(Y).
                all Y A(Y) & B(Y).
                all X A(X) <-> B(X).
                exists X C(X).""",
            [True, False, True, True]),

            ("""A(x,y).B(y).A(y,x).B(x).""",
            """all X exists Y A(X,Y) -> B(Y).
                all X all Y A(X,Y) -> B(Y).
                all X all Y A(X,Y).
                exists X exists Y C(X).""",
            [True, True, False, False]),

            ("""P(x,y).P(x,x).P(y,y).""",
            """all X P(X,X) # label(reflexivity) .
                all X all Y -(X = Y) -> -(P(X,Y) & P(Y,X)) # label(antisymmetry).
                all X all Y (P(X,Y) & P(Y,X)) # label(global_symmetry).
                all X all Y all Z (P(X,Y) & P(Y,Z) -> P(X,Z)) # label(transitivity). """,
            [True, True, False, True]),
            ("""P(x,y).P(x,x).P(y,y).PP(x,y).P(x,s).PP(x,s).P(y,s).PP(y,s).S(s,x,y).P(s,s).
                O(x,x).O(x,y).O(y,x).O(y,y).O(s,s).O(x,s).O(s,x).O(s,y).O(y,s).""",
            """all X P(X,X) # label(reflexivity) .
                all X all Y -(X = Y) -> -(P(X,Y) & P(Y,X)) # label(antisymmetry).
                all X all Y (P(X,Y) & P(Y,X)) # label(global_symmetry).
                all X all Y all Z (P(X,Y) & P(Y,Z) -> P(X,Z)) # label(transitivity). 
                all X all Y PP(X,Y) <-> P(X,Y) & - X=Y # label(PP_def). 
                all X all Y O(X,Y) <-> exists Z P(Z,X) & P(Z,Y) # label(O_def). 
                """,
            [True, True, False, True, True, True]),


        ]
        # model_text = """A(v).B(v).C(x)."""
        # model_text = """A(x,y).B(y)."""
        # model_text = """A(y,y).B(y)."""
        # model_text = """A(x,y).B(y).A(y,x).B(x)."""



        # axiom_text = "(all X all Y ((p(X,Y) & qqq(Y,X,ZZZ,z)) -> ((X)=(zz)))) # label(parthood_antysymmetry_Ad6)."
        # axiom_text = "(all X all Y (X = Y)) ."
        # axiom_text = "(all X all Y (X = y)) ."
        # axiom_text = "(all X all Y A(X,y)) ."
        # axiom_text = "(all X all Y exists Z A(X,Y,Z)) ."
        # axiom_text = "(all X all Y A(X,Y)) . (all Z B(Z)) ."
        # axiom_text = "all X A(X) <- B(X)."
        # axiom_text = ""
        # axiom_text = "exists X C(X)."
        # axiom_text = ""
        # axiom_text = "exists X A(X) & B(x)."

        p9variables = P9FreeVariablesExtractor()
        p9model = P9ModelReader()
        p9evaluator = P9Evaluator()
        p9explainer = P9Explainer()

        for model_text, axiom_text, ground_eval in model_texts_axioms_evals:
            print("testing axiom/model---->", axiom_text, model_text)
            modelAST: Tree = prover9_parser.parse(model_text)       
            axiomAST: Tree = prover9_parser.parse(axiom_text)
            print("parsed axiom --->", axiomAST.pretty())

            free_vars, axioms_signature = p9variables.extract_free_variables_and_signature(axiomAST)
            
            model = p9model.read_model(modelAST)
            p9evaluator.model = model
            

            print("after-model-visit-model---->", model)
            print("after-model-visit-model-signature---->", model.signature)

            if "=" in model.signature.predicates:
                raise TypeError(f"Equality was found in the model. It should not be there, and instead all constants should be assumed to be different")

            print("axioms has free variables?---->", free_vars)
            print("after-variables-extraction-axioms-signature---->", axioms_signature)

            evaluation = p9evaluator.evaluate(axiomAST)
            print(f"evaluation of {axiom_text} is >>>{evaluation}<<< given model {model} \n actual evaluation is >>>{ground_eval}<<<")
            assert evaluation == ground_eval, f"test failed, gonna print explanation... {p9explainer.explain(axiomAST)}"

        print("all the following tests where passed: ")
        for x,y,z in model_texts_axioms_evals:
            print(x)
            print(y)
            print(z)
            print("========================")
        print("all the previous tests where passed: ")
        
        # loop_on_file(file_path=r"C:\Users\Francesco\Desktop\Work_Units\fol_model_checker\test_p9_parsing.txt")
        # print("axioms signature after full variable extraction of file"+r"C:\Users\Francesco\Desktop\Work_Units\fol_model_checker\test_p9_parsing.txt", ....axioms_signature)
        # print(model)

if __name__ == "__main__":
    tests()