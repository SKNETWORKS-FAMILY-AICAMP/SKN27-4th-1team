from django.shortcuts import render

def goeijejoso(request):
    return render(request, 'generator/storymaker.html')
