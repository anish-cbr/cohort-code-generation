import sys
import json
import getopt
import logging
import jsonschema

gQidDict = {}
gQidsForConditionalRules = {}

gPreProcFuns = []
gValidateFuns = []
gConditionalFuns = []

def generate_conditional(file):
    file.write(f"###\n")
    file.write(f"# This function will handle all conditional checks for all questions\n")
    file.write(f"# Input  - dictionary of items. question id is the key and the answer is the value\n")
    file.write(f"#\n")
    file.write(f"# Output - Tuple (None, None) indicates success\n")
    file.write(f"#        - Tuple (qid, error_string) indicates failure\n")
    file.write(f"#\n")
    file.write(f"###\n")
    file.write(f"def validate_conditional_rules(vals):\n")

    for qid, rules in gQidsForConditionalRules.items():
        file.write(f"  try :\n")

        for rule in rules :
            name = rule["name"]
            qids = rule["qids"]

            op_str = f"    conditional_rule_{name}(vals[{qid}]"

            qids_dict = {qid : True}

            for q in qids:
                if q in qids_dict :
                    logging.error(f"incorrect conditional rule for qid : {qid}. Duplicate qid: {q} encountered.")
                    sys.exit(1)
                else :
                    if q in gQidDict :
                        qids_dict[q] = True
                    else:
                        logging.error(f"incorrect conditional rule for qid : {qid}. qid: {q} is not defined.")
                        sys.exit(1)

                op_str = op_str + f", vals[{q}]"

            params = rule.get("params", [])

            for p in params:
                if isinstance(p, str):
                    op_str = op_str + f", '{p}'"
                else:
                    op_str = op_str + f", {p}"

            op_str = op_str + f")\n"

            gConditionalFuns.append(op_str)

            file.write(op_str)

        file.write(f"  except Exception as e:\n")
        file.write(f'    return ({qid}, str(e))\n\n')

    file.write(f"  return (None, None)\n")


def generate_call_rule(type_str, rule_name, params, file) :
    op_str = ""

    for p in params:
        if isinstance(p, str):
            op_str = op_str + f", '{p}'"
        else:
            op_str = op_str + f", {p}"

    op_str = op_str + f")\n"

    if type_str == "preproc" :
        op_str = f"preproc_rule_{rule_name}(new_val" + op_str
        gPreProcFuns.append(op_str)
        op_str = f"    new_val = " + op_str
    elif type_str == "validate" :
        op_str = f"validate_rule_{rule_name}(new_val" + op_str
        gValidateFuns.append(op_str)
        op_str = f"    " + op_str
    else :
        logging.error(f"Unsupported type : {type_str}.")
        sys.exit(1)


    file.write(op_str)

def generate_call_preproc_rule(rule, file) :
    params = rule.get("params", [])

    generate_call_rule("preproc", rule["name"], params, file)

def generate_call_validate_rule(rule, file) :
    params = rule.get("params", [])

    generate_call_rule("validate", rule["name"], params, file)


def generate_func(grpCode, subgrpDetails, obj, file) :
    qid        = obj["qid"]
    dt         = obj["type"]
    name       = obj["name"]
    subgrpCode = obj["subgroupCode"]
    subgrpName = subgrpDetails[subgrpCode]
    desc       = obj["description"].split("\n")

    if qid in gQidDict :
       logging.error(f"Question id {qid} already exists.")
       sys.exit(1)

    isMandatory = obj.get("isMandatory", False)

    file.write(f"#############################\n")
    file.write(f"# Name          : {name}\n")
    file.write(f"# Description   : {desc[0]}\n")

    for item in desc[1:]:
        file.write(f"# {item}")

    file.write(f"# Group Code    : {grpCode}\n")
    file.write(f"# Subgroup Code : {subgrpCode}\n")
    file.write(f"# Subgroup Name : {subgrpName}\n")
    file.write(f"#############################\n")
    file.write(f"def validate_qid_{qid}(val) :\n")

    file.write(f"  if isinstance(val, str):\n")
    file.write(f"    val = val.strip()\n\n")

    if isMandatory == True :
        file.write(f"  if (val == '') or (val is None):\n")
        file.write(f"    return (val, 'Mandatory field value cannot be None')\n\n")
    else :
        file.write(f"  if (val == '') or (val is None):\n")
        file.write(f"    return (val, '')\n\n")

    file.write(f"  try :\n")

    file.write(f"    new_val = convert_dt(val, '{dt}')\n\n")

    if "preprocRules" in obj:
        file.write(f"    # Call the pre processing rules\n")

        for rule in obj["preprocRules"] :
            generate_call_preproc_rule(rule, file)

        file.write(f"\n")

    if "validationRules" in obj:
        file.write(f"    # Call the validation rules\n")

        for rule in obj["validationRules"] :
            generate_call_validate_rule(rule, file)

        file.write(f"\n")

    file.write('    return (new_val, "")\n\n')
    file.write("  except Exception as e:\n")
    file.write('    return (val, str(e))\n\n')

    if "conditionalRules" in obj:
        gQidsForConditionalRules[qid] = obj["conditionalRules"]

    gQidDict[qid] = obj

def print_funs(heading, funs) :
    if len(funs) > 0:
        print("--------------------")
        print(f"The following {heading} functions need to be implemented : \n")

        for fn in funs:
            print(f"{fn.strip()}\n")

def get_validated_subgroup_details(details):
    subgroup_dict = {}

    for detail in details:
        code = detail["code"]
        name = detail["name"]

        if code in subgroup_dict.keys():
            return ({}, f"Error - subgroup code :{code} is specified more than once in the file")

        subgroup_dict[code] = name

    return (subgroup_dict, "")
          

def main() :
    output_file   = None
    codebook_file = None
    schema_file   = None

    argv = sys.argv[1:]

    try:
        opts, args = getopt.getopt(argv, "s:c:o:", ["schema=", "codebook=", "output="])
    except e:
        logging.error(f"Error- {e}")
        sys.exit(1)

    for opt, arg in opts:
        if opt in ['-c', "--codebook"]:
            codebook_file = arg
        elif opt in ['-o', "--output"]:
            output_file = arg
        elif opt in ['-s', "--schema"]:
            schema_file = arg
        else :
            print(f"opt: {opt}, arg: {arg}")

    if output_file == None :
        logging.error("Please specify the output file name")
        sys.exit(1)

    if codebook_file == None :
        logging.Error("Please specify the codebook json file")
        sys.exit(1)

    if schema_file == None :
        logging.Error("Please specify the codebook schema json file")
        sys.exit(1)

    with open(schema_file, 'r') as file:
        schema = json.load(file)

    with open(codebook_file, 'r') as file:
        codebook = json.load(file)

    jsonschema.validate(instance=codebook, schema=schema)

    file = open(output_file, "x")

    file.write("from common import *\n\n")

    grpCode       = codebook["groupCode"]
    subgrpDetails = codebook["subgroupDetails"]

    (subgrpDetailsDict, error) = get_validated_subgroup_details(subgrpDetails)

    for q in codebook["questions"] :
        generate_func(grpCode, subgrpDetailsDict, q, file)

    generate_conditional(file)

    file.close()

    gPreProcFuns.sort()
    gValidateFuns.sort()

    print_funs("pre processing", gPreProcFuns)
    print_funs("validate", gValidateFuns)
    print_funs("Conditional Rules", gConditionalFuns)


if __name__=="__main__":
    main()
