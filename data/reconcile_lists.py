import csv
import itertools
import collections

if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser(description='Compare two files and identify their intersection and remainder.')
  parser.add_argument('file1', type=str,
                 help='First file to compare')
  parser.add_argument('file2', type=str,
                 help='Second file to compare')

  args = parser.parse_args()

  with open(args.file1, 'rb') as list_a:
    with open(args.file2, 'rb') as list_b:
      csvreader_a = csv.reader(list_a)
      csvreader_b = csv.reader(list_b)

      a = []    
      b = []
      for i in csvreader_a:
        a.append(i[0])

      for i in csvreader_b:
        b.append(i[0])

      a_multiset = collections.Counter(a)
      b_multiset = collections.Counter(b)

      overlap = list((a_multiset & b_multiset).elements())
      a_remainder = list((a_multiset - b_multiset).elements())
      b_remainder = list((b_multiset - a_multiset).elements())

      print 'overlap:', len(overlap)

      print 'a_remainder:', len(a_remainder)
      print a_remainder

      print 'b_remainder:', len(b_remainder)
      print b_remainder