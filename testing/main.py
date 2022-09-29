# Integration testing.
import os, sys, unittest






# load TestCase with discover modules.
dir_path = os.path.dirname(os.path.abspath(__file__))
module_path = os.path.join(dir_path, 'modules')
test = unittest.TestLoader().discover(module_path)

# run test and get result.
result = unittest.TextTestRunner(verbosity=2).run(test)


# exit code:
#   0: pass.
#   1: fail.
if result.errors or result.failures:
    sys.exit(1)
