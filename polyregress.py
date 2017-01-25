#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ***************************************************************************
# *   Copyright (C) 2014 by Paul Lutus                                      *
# *   lutusp@arachnoid.com                                                  *
# *   Modified in 2016 by Antonio Fiol                                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU General Public License for more details.                          *
# *                                                                         *
# *   You should have received a copy of the GNU General Public License     *
# *   along with this program; if not, write to the                         *
# *   Free Software Foundation, Inc.,                                       *
# *   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             *
# ***************************************************************************

import sys, math
import os.path

class Pair:
  def __init__(self,d):
    self.x,self.y = d
  def __repr__(self):
    return "Pair(%g,%g)" % (self.x,self.y)

class PolySolve:
  
  def show_mat(self,x):
    ys = len(x)
    xs = len(x[0])
    for r in x:
      sys.stdout.write("[ ");
      for c in r:
        sys.stdout.write("%16.12e," % c)
      print(" ]")
    print("************")
      
  def gj_swap(self,mat,i,k,j,m):
    temp = mat[i]
    mat[i] = mat[k]
    mat[k] = temp

  def gj_divide(self,mat,i,j,m):
    for q in range(j+1,m):
      mat[i][q] /= mat[i][j]
    mat[i][j] = 1

  def gj_eliminate(self,mat,i,j,n,m):
    for k in range(n):
      if(k != i and mat[k][j] != 0):
        for q in range(j+1,m):
          mat[k][q] -= mat[k][j] * mat[i][q]
        mat[k][j] = 0

  def gj_echelonize(self,mat):
    n = len(mat)
    m = len(mat[0])
    i = 0
    j = 0
    while(i < n and j < m):
      k = i
      while(k < n and mat[k][j] == 0): k += 1
      if(k < n):
        if(k != i):
          self.gj_swap(mat,i,k,j,m)
        if(mat[i][j] != 1):
          self.gj_divide(mat,i,j,m)
        self.gj_eliminate(mat,i,j,n,m)
        i += 1
      j += 1

  def calculate(self, polysize, data):
    n = len(data)
    p = polysize+1
    rs = 2*p-1
    # create precomputed data array
    mpc = [n]
    for r in range(1,rs):
      s = 0
      for v in data: s += math.pow(v.x,r)
      mpc +=  [s]
      
    # create and fill square matrix with added column
    m = [[mpc[r+c] for c in range(p)] + [0.0] for r in range(p)]
    
    # compute RH column
    for v in data: m[0][p] += v.y
    for v in data: m[1][p] += v.x * v.y
    for r in range(2,p):
      s = 0
      for v in data: s += math.pow(v.x,r) * v.y
      m[r][p] = s
    
    # compute polynomial terms
    self.gj_echelonize(m)

    if(polysize > n-1):
      print("Warning: polynomial degree > n-1.")

    return list(x[-1] for x in m)

  def format_equation(self,coeffs):
    y = "y ="
    e = 0
    for v in coeffs:
      
      s = -1 if(v < 0) else 1
      v = math.fabs(v)
      y += " -" if(s < 0) else " +"
      y += "%.12e" % v
      if(e > 0): y += "*x"
      if(e > 1): y += "^%d" % e
      e += 1
    return y


  def process(self):
    
    if(len(sys.argv) < 2):
      print('usage: %s [data list] or filename or - for stdin' % sys.argv[0])
      print('       data consists of polynomial degree followed by')
      print('       x y data pairs in any format.')
      quit()
  
    data = False
      
    flist = []
    
    # in principle, one could present data
    # in all three ways at once:
    #   from a file
    #   streamed from stdin
    #   as command-line args
    
    for arg in sys.argv[1:]:
      # stdin stream?
      if(arg == '-'):
        data = sys.stdin.read()
      # file?
      elif(os.path.isfile(arg)):
        with open(arg) as f:
          data = f.read()
      # data items as command-line arguments?
      else:
        try:
          flist.append(float(arg))
        except:
          None
          
    if(data):    
      for s in re.split("[^0-9Ee.+-]+",data):
        try:
          flist.append(float(s))
        except:
          None
    
    # first argument is polynomial degree
    polysize = int(flist.pop(0))

    # data must be in x,y pairs
    if(len(flist) % 2 != 0):
      print("Error: data not in form of x,y pairs.")
      sys.exit()
      
    # create paired data array
    data = list(map(Pair,list(zip(flist[::2],flist[1::2]))))

    coeffs = self.calculate(polysize,data)
    
    # print(result)
    print(self.format_equation(coeffs))

if __name__ == "__main__":
    PolySolve().process()

