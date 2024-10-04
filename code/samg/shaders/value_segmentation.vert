#version 450 core       
layout (location=0) uniform int Width; // width of the image in pixels        
layout (location=1) uniform int Height; // height of the image in pixels        
layout (location=2) uniform int Num_samples; // number of samples in the image (where we have real data)  
layout (location=3) uniform int Mode; // this is mode to compute the value: MEAN, MIN, MAX
layout (location=4) uniform int Null_value; // the index value that is considered as not belonging to any mask

layout (binding = 0,r8) uniform image2D Input_image_segments_ids; // the input image with the id of segment for each pixel
layout (binding = 1,r32f) uniform image2D Result_image; // the output is an image with a float for each pixel with the corresponding values of the interpolation
 
// the data of each compound (x,y,z). The positions are NOT normalized
// ¡¡ importante¡¡ Dado que el color son 4 flotantes, segun las reglas std430 de GLSL, vec4 necesita alinearse a
// 16 bytes. Si solo pongo x,y, y value, no se produce el alieneamiento a 16 bytes y se producen errores en la lectura
// por eso se añade una variable más para que se produzca el ajuste
struct Data
{ 
  float Pos_x;          
  float Pos_y;
  float Value;
  int Segment_id;
};

// the position data 
layout (binding=0,std430) buffer SSB_sample   
{ 
  Data Vec_data[]; 
};

// the position data 
layout (binding=1,std430) buffer SSB_valid_positions   
{ 
  int Vec_valid_positions[];
};

// the color of each sample position  
// layout (binding=2,std430) buffer SSB_sample_color
// {
//   vec4 Vec_color[];
// };



// function to compute the color using the minimum distance in the hypercube

void compute_minimum_distance(in ivec2 Pos,out vec4 Result_color,out bool Valid,out bool Copied)
{ 
  // read the segment_id of the pixel
  int Segment_id=int(imageLoad(Input_image_segments_ids,Pos).r*255.0);

  
  float Mean=0;
  float Min=1e10;
  float Max=-1;
  int Num_added_positions=0;

  // we have to compute the distance of the pixel to all the real samples (Num_samples)
  Copied=false;
  for (int i=0;i<Num_samples;i++){ 		
		// only the positive values can be used. Null_value is the segment value for no segment
		if (Vec_valid_positions[i]>0 && Vec_data[i].Segment_id!=Null_value && Vec_data[i].Segment_id==Segment_id){
			if (Num_added_positions==0 && Vec_valid_positions[i]==2) Copied=true;

			Mean=Mean+Vec_data[i].Value;
			Num_added_positions=Num_added_positions+1;
			if (Vec_data[i].Value<Min) Min=Vec_data[i].Value;
			if (Vec_data[i].Value>Max) Max=Vec_data[i].Value;
		}
	}

	if (Num_added_positions>0){
	  Mean=Mean/float(Num_added_positions);
	  Valid=true;
	}
	else{
	  Min=0;
	  Max=0;
	  Valid=false;
	}

	float Final_value=0;
	switch(Mode){
	case 2: // mean
		Final_value=Mean;
		break;
	case 3: // minimum
		Final_value=Min;
		break;
	case 4: // maximum
		Final_value=Max;
		break;
	}
	Result_color=vec4(Final_value,0,0,1);
} 

// main 

void main(void)         
{
  // A vertex is emitted for each pixel. There are RowsxCols pixels. Now the inverse convertion is applied
  // The column
  int Pos_x=gl_VertexID % Width;
	// The row
  int Pos_y=gl_VertexID / Width;
  // the pos that will be used to scan the texture
  ivec2 Pos=ivec2(Pos_x,Pos_y);    
  bool Valid;
  bool Copied;
      
  // The initial color is black
  vec4 Result_color=vec4(0,0,0,1);          
         
  // Check if the alpha value is 0 -> This part is no valid
//   if (Color_normalized_input_image.a==0){
// 		// draw a chessboard texture using the module operator -> quares of size 10
//     if (mod(Pos.x,20)<10 && mod(Pos.y,20)<10) Result_color=vec4(1,0,0,1);
//     else Result_color=vec4(0,0,0,1);
//   }
//   else{
// 		// It is normal color
//     compute_minimum_distance(Pos,Result_color);
//   }

  compute_minimum_distance(Pos,Result_color,Valid,Copied);

  if (Valid==false){
	if (mod(Pos.x,10)<5 && mod(Pos.y,10)<5) Result_color=vec4(1,0,0,1);
    else Result_color=vec4(0,0,0,1);
  }
  else{
	if (Copied==true){
	  if (mod(Pos.x,10)>8) Result_color=vec4(0,0,0,1);
	}
  }

//   if (Copied==true) Result_color=vec4(1,0,0,1);
//   if (Vec_valid_positions[2]==2) Result_color=vec4(1,0,0,1);
//   else Result_color=vec4(0,0,0,1);

  // save the result
  imageStore(Result_image,Pos,Result_color);  
} 
