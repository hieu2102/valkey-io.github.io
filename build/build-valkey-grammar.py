#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ARG_TOKEN_JSON_KEY="token"
REGEX_SPECIAL_CHARS= ["\\", "^", "$", ".", "|", "?", "*", "+", "(", ")", "[", "{"]

def find_json_key(json_input, lookup_key):
    if isinstance(json_input, dict):
        for k, v in json_input.items():
            if k == lookup_key:
                yield v
            else:
                yield from find_json_key(v, lookup_key)
    elif isinstance(json_input, list):
        for item in json_input:
            yield from find_json_key(item, lookup_key)

def find_command_args(cmd_json_data: dict):
    args: set[str] = set()
    arg_tokens = find_json_key(cmd_json_data, ARG_TOKEN_JSON_KEY)
    for token in arg_tokens:
        if not isinstance(token, str):
            continue
        args.add(token.lower())
    return args

def parse_cmd_json(cmd_json_filename: str):
    with open(cmd_json_filename, "r", encoding= "utf-8") as f:
        data = json.load(f)
    cmd_name =next(iter(data)).lower()
    cmd_args = find_command_args(data)
    return cmd_name, cmd_args


def parse_cmd_json_dir(dirname: str):
    d = Path(dirname)
    commands: set[str]= set()
    args: set[str] = set()
    for cmd_json_file in list(d.glob("*.json")):
        cmd, arg = parse_cmd_json(cmd_json_file)
        if cmd is None:
            print(f"missing command token: ${cmd_json_file}")
        commands.add(cmd)
        args  = args | arg
    return commands, args

def build_match(tokens: set[str] | list[str]):
    # random special char first, so that regex chars can be escaped easier
    regex_str = "\r".join(tokens)
    for c in REGEX_SPECIAL_CHARS:
        if c in regex_str: 
            regex_str = regex_str.replace(c, "\\"+c)
    # wrap the regex str in case-insensitive mode (?i) + word boundary (\b)
    return f"(?i:\\b({regex_str.replace("\r", "|")})\\b)"


project_root_dir = Path(sys.argv[1])
output_file = str(project_root_dir) + "/grammars/valkey.json"
grammar = {
    "displayName": "valkey",
    "name": "valkey",
    "patterns": [
        {
            # quoted string
            "match": r'"(.+?)"',
            "name":"string.quoted.double"
        },
        {
            # single quoted string
            "match": r"'(.+?)'",
            "name":"string.quoted.single"
        },
        {
            # terminal prompt
            "match": r'^(.*?>)',
            "name":"comment"
        },
        {
            # output index
            "match": r'^(\s*\d+\)\s*\d*\)?)',
            "name":"comment"
        },
        {
            "match": r'\b(BUSY|BUSYGROUP|BUSYKEY|CLUSTERDOWN|CROSSSLOT|DENIED|ERR|EXECABORT|INPROG|INVALIDOBJ|IOERR|LOADING|MASTERDOWN|MISCONF|NOAUTH|NOGOODSLAVE|NOGROUP|NOMASTERLINK|NOPERM|NOPROTO|NOQUORUM|NOREPLICAS|NOSCRIPT|NOTBUSY|OOM|READONLY|REDIRECT|TRYAGAIN|UNBLOCKED|UNKILLABLE|WRONGPASS|WRONGTYPE)\b',
            "name":"constant.language",
        },
        {
            # ACL string
            "match": r'\s(\+@?[\w|]+|-@?[\w|]+|~\*)\s',
            "name":"constant.language"
        },
        {
            # ACL constant
            "match": r'(?i:\b(on|off|nopass)\b)',
            "name": "variable.parameter"
        },
        {
            # datatype
            "match": r'\((error|integer|double|nil|true|false|empty array|empty hash|empty set|empty push|empty aggregate type)\)',
            "name": "support.type"
        },  
    ],
    "scopeName": "source.valkey"
}
for commands_dir in list(project_root_dir.glob("*build*command*-json")):
    cmds,args = parse_cmd_json_dir(commands_dir)
    if len(cmds) >0:
        grammar["patterns"].append(
        {
            "name": "support.function",
            "match": build_match(cmds)
        }
    )
    if len(args)> 0:
        grammar["patterns"].append({
            "name": "variable.parameter",
            "match": build_match(args)
        }
    )


with open(output_file, 'w') as w:
    json.dump(grammar, w, indent=4)