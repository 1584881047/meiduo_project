def myMiddleWare(get_response):

    def innerMiddleWear(request):


        response = get_response(request)

        return response

    return innerMiddleWear
