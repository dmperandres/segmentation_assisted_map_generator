import csv
import sys
from dataclasses import dataclass, field
from typing import List

TOP_LEFT = 0

@dataclass
class sample_data:
	max_value : float
	values: List[float] = field(default_factory=list)

class project_data:
	def __init__(self):
		self.project_name = None
		self.author = None
		self.date = None
		self.device = None
		self.tube = None
		self.width_cm = 0
		self.height_cm = 0
		self.width_px = 0
		self.height_px = 0
		self.cs_origin = TOP_LEFT
		self.height_cm = 0
		self.coordinates_x = []
		self.coordinates_y = []
		self.xrf_data = {}
		self.xrd_data = {}

	def load(self, file_name, width: int, height: int):
		width = float(width - 1)
		height = float(height - 1)

		with open(file_name, 'r') as file:
			lines = file.readlines()
			pos = 0
			while pos < len(lines):
				line = lines[pos].strip()
				pos +=1
				tokens = line.split(';')
				if tokens[0] == 'PROJECT_NAME':
					self.project_name = tokens[1]
				elif tokens[0] == 'AUTHOR':
					self.author = tokens[1]
				elif tokens[0] == 'DATE':
					self.date = tokens[1]
				elif tokens[0] == 'DEVICE':
					self.device = tokens[1]
				elif tokens[0] == 'TUBE':
					self.tube = tokens[1]
				elif tokens[0] == 'WIDTH_CM':
					self.width_cm = float(tokens[1].replace(',','.'))
				elif tokens[0] == 'HEIGHT_CM':
					self.height_cm = float(tokens[1].replace(',','.'))
				elif tokens[0] == 'WIDTH_PIXEL':
					self.width_px = float(tokens[1])
				elif tokens[0] == 'HEIGHT_PIXEL':
					self.height_px = float(tokens[1])
				elif tokens[0] == 'CS_ORIGIN':
					self.cs_origin = tokens[1]
				elif tokens[0] == 'X':
					for pos1 in range(2,len(tokens)):
						self.coordinates_x.append(round(float(tokens[pos1])*width))
				elif tokens[0] == 'Y':
					for pos1 in range(2,len(tokens)):
						if self.cs_origin == 'TOP_LEFT':
							# invert for OpenGL
							self.coordinates_y.append(round((1.0-float(tokens[pos1]))*height))
						else:
							self.coordinates_y.append(round(float(tokens[pos1])*height))
				elif tokens[0] == 'XRF':
					max = -1.0
					data = [0]*len(self.coordinates_x)
					for pos1 in range(len(self.coordinates_x)):
						token=tokens[pos1+2]
						token=tokens[pos1+2].replace(',','.')
						if token != '':
							value = float(token)
							data[pos1] = value
							if value > max:
								max = value
						else:
							print("Error in element ", tokens[1], " in pos ", pos1)
					#normalization
					for pos1 in range(len(self.coordinates_x)):
						data[pos1] /= max
					self.xrf_data[tokens[1]]=sample_data(max, data)
				elif tokens[0] == 'XRD':
					max = -1.0
					data = [0] * len(self.coordinates_x)
					for pos1 in range(len(self.coordinates_x)):
						token = tokens[pos1 + 2].replace(',', '.')
						if token != '':
							value = float(token)
							data[pos1] = value
							if value > max:
								max = value
						else:
							print("Error in pigment ", tokens[1], " in pos ", pos1)
					# normalization
					for pos1 in range(len(self.coordinates_x)):
						data[pos1] /= max
					self.xrd_data[tokens[1]] = sample_data(max, data)

		# self.xrf_data.sort(key = lambda x : x.name)
		# self.xrd_data.sort(key = lambda x:  x.name)
