#version 450 core
layout (location=0) in vec3 vertex;
layout (location=1) in vec2 texture_coordinates;

layout (location=10) uniform mat4 matrix;

out vec2 texture_coordinates_out;

void main(void)
{
    texture_coordinates_out=texture_coordinates;
    gl_Position=matrix*vec4(vertex,1);
}
