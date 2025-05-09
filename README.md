## Model Checker For First-Order Logic
This is a model checker for first-order logic. That is, given a model and a theory, it is checked that the model satisfies the theory. 
The model is supplied as a list of assertions, with the convention that each and every true assertion is stated and each and every false assertion is not stated. 
The theory is supplied as a list of axioms. 

The syntax is similar to that of [Prover9](https://www.cs.unm.edu/~mccune/mace4/).

As of now two evaluation strategies have been implemented: 
- a simple, nested-loop style brute-force approach that evaluates all axioms sequentially.
- an equivalence-based strategy, that reduces the size of the quantification domain for each quantifier: given the signature of the quantified formula, all the constants that cannot be distinguished by the symbols in the signature are collapsed together. 
In both strategies if an axioms is false the algorithm stops and explains why the axioms was evaluated false.

A third strategy is under development:
- a further reduction of the quantification domains based on the a-priori determination of simple range expressions that the quantified variables must satisfy.   

Simply run check.py supplying the path to a file containing a model and the path to a file containing a theory (e.g. `>python check.py DOLCE-clay-statue-model.p9 DOLCE-clay-statue-axioms.p9`). 
Default evaluation strategy is btute force. Supply a value to `--options` (currently can only be `equivalence`) to change the evauation strategy. 

Some tests are present in `tests.py`. They can be run by executing that file. The `DOLCE-clay-statue` model and axioms files are an example of model and theory files, as well as an additional tests. 

Note that the complexity of the algorithm is O(c^a) where c is the number of constants in the model, and a is the maximum nesting-depth of quantifiers.   

## TODOS
- Implement faster strategies in addition to brute force and equivalence. 
- Implement simplified treatment for defined predicates.
- Implement functions.

## Some Finer Details
- The syntax is similar to prover9. However, *functions are not implemented* (except for constant symbols). Additionally, the `!=` operator is not implemented, and the default prover9 operator priority has been hardcoded in the grammar and cannot be changed. 
- Note that the model is specified following a closed-world-style convention. 
- Equality is not implemented in the model specification: it is assumed that differently named constants are different; and that all the constant that exist in the model are exactly those mentioned in some assertion.  
- The algorithm is not "smart": e.g. `all X0 all X1 all X2 ... all X100 phi | - phi` is a tautology but will not be evaluated.
- Explanation works by visiting an axiom parsing tree and specifying for each node its truth value for the relevant variables substitutions. 
