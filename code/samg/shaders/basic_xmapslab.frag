#version 450 core                                    

// program to render the layers using textures. There is a max number of simultaneous visible layers

layout (location=20) uniform int Num_textures; // num of textures
layout (location=21) uniform vec3 Background_color; // background color
                                                     
layout (location=50) uniform int Type[10]; // type of layer
layout (location=60) uniform float Transparency[10]; // value of transparency for the layer
layout (location=70) uniform int Inversion[10]; // if there is inversion in the layer
layout (location=80) uniform int Color_mixing[10];
                                                     
// there are 8 textures at most
layout (binding=0) uniform sampler2D Textures[8];

// the texture coordinate
in vec2 texture_coordinates_out;
                                                     
out vec4 frag_color;

void main(void)                                      
{                                      
  // initialize to the background color
  vec4 Color1=vec4(Background_color,1);
  
  vec4 Color_texture;
  vec4 Color_texture1;
  int Mask_active=0;
  int Mask_value=1;
  
  // compute the final color by composing the obtained color of each texture
  // the textures are ordered in depth, from the farthest, at 0, to the nearest, at Num_textures-1  
  for (int i=0;i<Num_textures;i++){
	// get the color
	Color_texture=texture(Textures[i],texture_coordinates_out);


// 	if (Type[i]<2){
// 		if (Color_mixing[i]==1){
// 			if (Color_texture.a!=0)	Color1=mix(Color1,Color_texture,(1-Transparency[i])*Color_texture.a);
// 		}
// 		else{
// 			Color1=vec4(0,1,0,1);
// 		}
// 	}
// 	else{
// 		Color1=vec4(1,0,0,1);
// 	}

	if (Type[i]<2){
		// for basic=0 and maps = 1 layers
		// current combination -> decal
		if (Color_mixing[i]==1){
			if (Color_texture.a!=0)	Color1=mix(Color1,Color_texture,(1-Transparency[i])*Color_texture.a);
			//if (Color_texture.a==0) Color1=vec4(0,0,1,1);
		}
		else{
			Color1=mix(Color1,Color_texture,(1-Transparency[i])*Color_texture.a);
		}
	}
	else{
		// layers for borders and other effects
		// check that the valued is valid (remember that componet w=0 implies that is not valid
		if (Color_texture.a==1){
			if (Inversion[i]==1){
				// if there is inversion
				Color_texture=vec4(vec3(1)-vec3(Color_texture),Color_texture.a);
			}

			// compute the final result as the linear interpolation of the previous color and the current one, taking into account the transparency
			Color1=mix(Color1,Color_texture,1-Transparency[i]);
		}
	}
  }

  // output the final color
  frag_color=Color1;
//   frag_color=vec4(0,0,0,1);
}
