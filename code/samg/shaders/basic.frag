#version 450 core

uniform sampler2D texture_image;

in vec2 texture_coordinates_out;
out vec4 frag_color;

void main(void)
{
    frag_color=texture(texture_image,texture_coordinates_out);
}
