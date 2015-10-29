#!/usr/bin/python
# Compares two drules files and produces a merged result.
# Also prints differences (missing things in drules1) to stdout.
import sys, re
import copy
import drules_struct_pb2

def read_drules(drules):
  """Parses the structure and extracts elements for lowest and highest zooms
  for each rule."""
  result = {}

  for rule in drules.cont:
    zooms = [None, None]
    for elem in rule.element:
      zoom = rule.scale
      if zoom >= 0:
        if zooms[1] is None or zoom > zooms[1].scale:
          zooms[1] = elem
        if zooms[0] is None or zoom < zooms[0].scale:
          zooms[0] = elem
    if zooms[0] is not None:
      name = str(rule.name)
      if name in result:
        if result[name][0].scale < zooms[0].scale:
          zooms[0] = result[name][0]
        if result[name][1].scale > zooms[1].scale:
          zooms[1] = result[name][1]
      result[name] = zooms
  return result

def zooms_string(z1, z2):
  """Prints 'zoom N' or 'zooms N-M'."""
  if z2 != z1:
    return "zooms {}-{}".format(min(z1, z2), max(z1, z2))
  else:
    return "zoom {}".format(z1)

def create_diff(zooms1, zooms2):
  """Calculates difference between zoom dicts, and returns a tuple:
  (add_zooms_low, add_zooms_high, add_types), for missing zoom levels
  and missing types altogether. Zooms are separate to preserve sorting
  order in elements."""
  add_elements_low = {}
  add_elements_high = {}
  seen = set([x for x in zooms2])
  for typ in zooms1:
    if typ not in zooms2:
      print "{}: not found in the alternative style; {}".format(typ, zooms_string(zooms1[typ][0].scale, zooms1[typ][1].scale))
    else:
      seen.remove(typ)
      if zooms2[typ][0].scale < zooms1[typ][0].scale:
        print "{}: missing low {}".format(typ, zooms_string(zooms2[typ][0].scale, zooms1[typ][0].scale - 1))
        if not typ in add_elements_low:
          add_elements_low[typ] = []
        for z in range(zooms2[typ][0].scale, zooms1[typ][0].scale):
          fix = copy.deepcopy(zooms1[typ][0])
          fix.scale = z
          add_elements_low[typ].append(fix)
      elif zooms2[typ][0].scale > zooms1[typ][0].scale:
        print "{}: extra low {}".format(typ, zooms_string(zooms1[typ][0].scale, zooms2[typ][0].scale - 1))

      if zooms2[typ][1].scale > zooms1[typ][1].scale:
        print "{}: missing high {}".format(typ, zooms_string(zooms1[typ][1].scale + 1, zooms2[typ][1].scale))
        if not typ in add_elements_high:
          add_elements_high[typ] = []
        for z in range(zooms1[typ][1].scale, zooms2[typ][1].scale):
          fix = copy.deepcopy(zooms1[typ][1])
          fix.scale = z + 1
          add_elements_high[typ].append(fix)
      elif zooms2[typ][1].scale < zooms1[typ][1].scale:
        print "{}: extra high {}".format(typ, zooms_string(zooms2[typ][1].scale + 1, zooms1[typ][1].scale))

  add_types = []
  for typ in seen:
    print "{}: missing completely; {}".format(typ, zooms_string(zooms2[typ][0].scale, zooms2[typ][1].scale))
    cont = drules_struct_pb2.ClassifElementProto()
    cont.name = typ
    for z in range(zooms2[typ][0].scale, zooms2[typ][1].scale):
      fix = copy.deepcopy(zooms2[typ][0])
      fix.scale = z
      cont.element.extend([fix])
    add_types.append(cont)

  return (add_elements_low, add_elements_high, add_types)

def apply_diff(drules, diff):
  """Applies diff tuple (from create_diff) to a drules set."""
  result = drules_struct_pb2.ContainerProto()
  for rule in drules.cont:
    typ = str(rule.name)
    fix = drules_struct_pb2.ClassifElementProto()
    fix.name = typ
    if typ in diff[0]:
      fix.element.extend(diff[0][typ])
    if rule.element:
      fix.element.extend([el for el in rule.element])
    if typ in diff[1]:
      fix.element.extend(diff[1][typ])
    result.cont.extend([fix])
  result.cont.extend(diff[2])
  return result

if __name__ == '__main__':
  if len(sys.argv) <= 3:
    print 'Usage: {} <drules1.bin> <drules2.bin> <drules_out.bin> [drules_out.txt]'.format(sys.argv[0])
    sys.exit(1)

  drules1 = drules_struct_pb2.ContainerProto()
  drules1.ParseFromString(open(sys.argv[1]).read())
  drules2 = drules_struct_pb2.ContainerProto()
  drules2.ParseFromString(open(sys.argv[2]).read())

  zooms1 = read_drules(drules1)
  zooms2 = read_drules(drules2)
  diff = create_diff(zooms1, zooms2)
  merged = apply_diff(drules1, diff)

  with open(sys.argv[3], 'wb') as f:
    f.write(merged.SerializeToString())
  if len(sys.argv) > 4:
    with open(sys.argv[4], 'wb') as f:
      f.write(unicode(merged))
