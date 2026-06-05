from django.shortcuts import render

def index(request):
    return render(request, 'archive/index.html')


def sillokgwan(request):
    return render(request, 'archive/chatbot.html')


def geumgirok(request):
    return render(request, 'archive/archive.html')
