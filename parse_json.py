#!/usr/bin/python3

"""Parses Heaven's Vault's GameData.json.

This allows us to generate all words in the game.
"""

import argparse
import collections
import json
import re

# Out-of-game data: To use the ancientrunes font, we must map rune names to
# characters. This essentially requires hardcoding the knowledge of what all
# the runes are, alas.
FONTMAP = {
    'verb': '"',
    'of': "'",
    'property': '(',
    'noun': ')',
    'primitive': ',',
    'joinglyph2': '.',
    '0': '0',
    '1': '1',
    '2': '2',
    '3': '3',
    '4': '4',
    '5': '5',
    '6': '6',
    '7': '7',
    '8': '8',
    '9': '9',
    'joinglyph1': ':',
    'quality': ';',
    'water': '=',
    'query': '?',
    'truth': 'a',
    'past_tense': 'b',
    'time': 'c',
    'beginning': 'd',
    'possession': 'e',
    'many': 'f',
    'say': 'g',
    'light': 'h',
    'high': 'i',
    'being': 'j',
    'creature': 'k',
    'life': 'l',
    'separate': 'm',
    'join': 'n',
    'circle': 'o',
    'knowledge': 'p',
    'food': 'q',
    'person': 'r',
    'motion': 's',
    'plant': 't',
    'place': 'u',
    'rock': 'v',
    'and': 'w',
    'not': 'x',
    'mineral': 'y',
    'heat': 'z',
}

# Constants to use instead of string lookup keys
NAME = 'name'
ATOM = 'atom'
TYPE = 'type'
PREFIX = 'prefix'
MODIFIER = 'modifier'
PUNCTUATION = 'punctuation'

Atom = collections.namedtuple('Atom', [NAME, TYPE])
Word = collections.namedtuple('Word',
        [NAME, 'equivalences', 'components', 'atoms'])

def compute_atoms(atoms_list):
    """Computes and returns the atom dictionary"""
    atoms = {FONTMAP[x[NAME].casefold()] : Atom(x[NAME], x['atomType']) for x in atoms_list}
    atoms[FONTMAP['joinglyph1']] = Atom('joinGlyph1', PUNCTUATION)
    atoms[FONTMAP['joinglyph2']] = Atom('joinGlyph2', PUNCTUATION)
    atoms[FONTMAP['primitive']] = Atom('primitive', PUNCTUATION)
    for atom_name, atom in FONTMAP.items():
        if atom not in atoms:
            raise RuntimeError('%s not found in data' % atom_name)
    return atoms


def canonicalize(atom_string, atoms):
    """Puts punctuation into words in the proper places.

    This algorithm is directly reverse-engineered from the C# code.
    """
    # Remove existing punctuation. Surprisingly, the algorithm does not build
    # words by putting punctuation between subwords, but instead flattens
    # everything and then adds punctuation fresh each time.
    squash_dict = {ord(x):None for x,y in atoms.items() if y.type == PUNCTUATION}
    atom_string = atom_string.translate(squash_dict)
    orig_len = len(atom_string)
    # Deduplicate certain atoms in very specific circumstances. This handles
    # changing verbs tenses, etc, but it also does some weirder
    # omissions that make less sense.
    new_list = []
    current = None
    for atom in atom_string:
        atom_type = atoms[atom].type
        if atom_type in (PREFIX, TYPE):
            if current != atom:
                current = atom
            else:
                continue
        elif atom_type == ATOM:
            current = None
        new_list.append(atom)
    atom_string = ''.join(new_list)
    # We need to maintaim the length specially, because of an edge-case: The
    # original algorithm inserts into the list as it iterates, increasing the
    # length, and since there's a length test we need to emulate that to get
    # proper behavior.
    curr_len = len(atom_string)
    # The core loop that adds punctuation
    prev_atom = atom_string[0]
    new_list = [prev_atom]
    prev_type = atoms[prev_atom].type
    needs_join = prev_type == PREFIX
    for atom in atom_string[1:]:
        atom_type = atoms[atom].type
        # This rule is responsible for most of the dots in words.
        # Note that post-type transitions take precedence over pre-prefix
        # transitions, which is why you see dots in a lot of places you might
        # expect colons.
        if prev_type == TYPE and atom_type != TYPE:
            new_list.append('.')
            curr_len += 1
        # The length part of this rule is why certain possessives don't have a
        # dot, effectively becoming indistinguishable from "of NOUN". Since
        # this is applied globally, some compounds get the dot dropped when
        # included in a larger word.
        elif prev_atom == "'" and curr_len <= 4:
            new_list.append('.')
            curr_len += 1
        # This adds in all the colons. I'm not sure what the justification is
        # for skipping the first one in certain narrow circumstances, but it's
        # why "parent" and several other "r.e"-starting words don't have an
        # colon joining them to the next subword.
        elif atom_type == PREFIX and prev_type != PREFIX:
            if needs_join or prev_type != ATOM:
                new_list.append(':')
                curr_len += 1
            needs_join = True
        prev_atom = atom
        new_list.append(prev_atom)
        prev_type = atom_type
    atom_string = ''.join(new_list)
    if orig_len == 2 and atoms[atom_string[0]].type == PREFIX:
        atom_string += ','
    # Remove all colons, but only if it leaves the final result at three
    # glyphs or less.
    pruned = atom_string.replace(':', '')
    if len(pruned) <= 3:
        atom_string = pruned
    return atom_string


def create_word(word, words, atoms):
    """Computes the atom-string for word, if needed"""
    if word.atoms is not None:
        return word.atoms
    atom_list = []
    for part in word.components:
        part = part.casefold()
        atom = FONTMAP.get(part)
        if atom:
            atom_list.append(atom)
        else:
            subword = words[part]
            sub_atoms = create_word(subword, words, atoms)
            atom_list.append(sub_atoms)
    atom_string = canonicalize(''.join(atom_list), atoms)
    words[word.name.casefold()] = word._replace(atoms=atom_string)
    return atom_string


def compute_words(words_list, atoms):
    """Computes and returns the word dictionary"""
    words = {x[NAME].casefold() : Word(
        x[NAME], x.get('equivalences', []), x['components'], None) for x in words_list}
    for word in words.values():
        create_word(word, words, atoms)
    return words


def lookup(word, word_dict):
    """Find the relevant atom_string for a word"""
    char = FONTMAP.get(word)
    if char:
        return char
    return word_dict[word].atoms


def parse_original(original_file):
    """Parse original wikitable content into a dictionary, keyed by atoms"""
    words = {}
    key = None
    pending = []
    # <nowiki> tags are optional. Meant to extract the text inside the
    # template.
    pat = re.compile(r'\| \{\{ALB\|(?:<nowiki>)?([^<>]*)(?:</nowiki>)?\}\}')
    pat2 = re.compile(r'\| ?(.*)')
    for line in original_file:
        line = line.rstrip()
        if line == '|-':
            if key is not None:
                if key in words:
                    pending = words[key] + ["*duplicate*"] + pending
                words[key] = pending
                key = None
                pending = []
            continue
        if key is None:
            match = pat.fullmatch(line)
            if not match:
                raise ValueError("Couldn't match " + line)
            key = match[1]
        else:
            match = pat2.fullmatch(line)
            if not match:
                raise ValueError("Couldn't match " + line)
            pending.append(match[1])
    if key is not None:
        if key in words:
            pending = words[key] + ["*duplicate*"] + pending
        words[key] = pending
    return words


ALB_TABLE = {ord(x): f'&#{ord(x)};' for x in "';:="}


def alb(atoms, use_nowiki):
    """Format atoms using Template:ALB"""
    if use_nowiki:
        return '{{ALB|<nowiki>' + atoms + '</nowiki>}}'
    return '{{ALB|' + atoms.translate(ALB_TABLE) + '}}'


def print_wiki_word(word, word_dict, fields, use_nowiki):
    """Print a wikitable entry for a single word"""
    orig_names = {}
    if fields:
        if fields[0].endswith('(s)'):
            orig_names = {fields[0][:-3]: True, fields[0][:-3] + 's': True}
        else:
            orig_names = {x.strip(): True for x in fields[0].split('/')}
    names = []
    for name in [word.name] + word.equivalences:
        if name in orig_names:
            names.append(name)
            del orig_names[name]
        else:
            names.append(name + '?')
    for name in orig_names:
        names.append('!!' + name + '!!')
    print('|-')
    print('| ' + alb(word.atoms, use_nowiki))
    print('| ' + ' / '.join(names))
    print('| ' + ' '.join(
        alb(lookup(x.casefold(), word_dict), use_nowiki) + f' ({x})'
        for x in word.components))
    if fields and len(fields) >= 2 and fields[1]:
        print('| ' + fields[1])


def generate_wikitable(word_dict, original, use_nowiki=True):
    """Print wikitable for the full word list"""
    words = list(word_dict.values())
    words.sort(key=lambda x:x.name.casefold())
    known_atoms = {x.atoms for x in word_dict.values()}

    original_list = list(original.items())
    original_list.sort(key=lambda x:x[1][0].casefold())
    for atoms, fields in original_list:
        # Output all the original bits that don't appear in the extracted data
        # first. They're either wrong, or the extracted data is wrong. Either
        # way, we want to see it up front.
        if atoms in known_atoms:
            continue
        print('|-')
        print('| ' + alb(atoms, use_nowiki))
        # Only print the first 3 fields, we're trimming the last one.
        # We're also swapping the order of the last two fields.
        print('| ' + fields[0])
        if len(fields) >= 2:
            if len(fields) >= 3:
                print('| ' + fields[2])
            else:
                print('|')
            print('| ' + fields[1])

    for word in words:
        print_wiki_word(word, word_dict, original.get(word.atoms), use_nowiki)


def main():
    """main(). Thanks, pylint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game_data', type=argparse.FileType('r'),
        help="The GameData.json file")
    parser.add_argument('-w', '--wikitable', action='store_true',
        help="Output words as the body of a wiki table")
    parser.add_argument('-m', '--merge', type=argparse.FileType('r'),
        help="Original wiki table content to merge")
    parser.add_argument('-q', '--quote', action='store_true',
        help="Use &apos; instead of <nowiki> to escape Ancient words")

    args = parser.parse_args()
    data = json.load(args.game_data)
    atoms = compute_atoms(data['atoms'])
    words = compute_words(data['words'], atoms)
    original_content = {}
    if args.merge:
        original_content = parse_original(args.merge)
    if args.wikitable:
        generate_wikitable(words, original_content, not args.quote)


if __name__ == '__main__':
    main()
