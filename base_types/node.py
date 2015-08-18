import re
import bpy
import random
from bpy.props import *
from bpy.app.handlers import persistent
from .. utils.nodes import getNotUsedSocketName
from . node_function_call import getNodeFunctionCallOperatorName
from .. utils.nodes import getAnimationNodeTrees

class AnimationNode:
    identifier = StringProperty(name = "Identifier", default = "")

    activeInputIndex = IntProperty()
    activeOutputIndex = IntProperty()

    searchTags = []
    onlySearchTags = False
    isDetermined = False
    isAnimationNode = True

    @classmethod
    def poll(cls, nodeTree):
        return nodeTree.bl_idname == "an_AnimationNodeTree"

    # On creation
    def init(self, context):
        self.identifier = createIdentifier()
        self.create()

    def create(self):
        '''Implement this in all subclasses'''
        pass

    # On node tree changes
    def update(self):
        '''Don't use this function at all'''
        pass

    def edit(self):
        """Optional function for subclasses"""
        pass

    # On node duplication
    def copy(self, sourceNode):
        self.identifier = createIdentifier()
        self.duplicate(sourceNode)

    def duplicate(self, sourceNode):
        """Optional function for subclasses"""
        pass

    # On node deletion
    def free(self):
        self.delete()

    def delete(self):
        """Optional function for subclasses"""
        pass

    def draw_buttons(self, context, layout):
        self.draw(layout)

    def draw(self, layout):
        pass

    def drawAdvanced(self, layout):
        layout.label("Has no advanced settings")


    def functionOperator(self, layout, functionName, text = "", icon = "NONE", description = "", data = None):
        idName = getNodeFunctionCallOperatorName(description)
        props = layout.operator(idName, text = text, icon = icon)
        props.nodeTreeName = self.id_data.name
        props.nodeName = self.name
        props.functionName = functionName
        props.callWithData = data is not None
        props.data = str(data)

    def removeSocket(self, socket):
        index = socket.index
        if socket.is_output:
            if index < self.activeOutputIndex: self.activeOutputIndex -= 1
        else:
            if index < self.activeInputIndex: self.activeInputIndex -= 1
        socket.sockets.remove(socket)

    def toogleSocketEditing(self):
        if len(self.sockets) == 0: return
        self.setSocketEditing(not self.sockets[0].editInNode)

    def setSocketEditing(self, editInNode = False):
        for socket in self.sockets:
            socket.editInNode = editInNode
        bpy.context.area.tag_redraw()

    def getNotUsedSocketName(self, prefix = "socket"):
        return getNotUsedSocketName(self, prefix)

    def getLinkedOutputIdentifiers(self):
        linkedIdentifiers = [socket.identifier for socket in self.outputs if socket.isLinked]
        return linkedIdentifiers

    @property
    def activeInputSocket(self):
        if len(self.inputs) == 0: return None
        return self.inputs[self.activeInputIndex]

    @property
    def activeOutputSocket(self):
        if len(self.outputs) == 0: return None
        return self.outputs[self.activeOutputIndex]

    @property
    def sockets(self):
        return list(self.inputs) + list(self.outputs)

    @property
    def inputNames(self):
        return {socket.identifier : socket.identifier for socket in self.inputs}

    @property
    def outputNames(self):
        return {socket.identifier : socket.identifier for socket in self.outputs}

    def getExecutionCodeString(self):
        code = self.getExecutionCode()
        if isinstance(code, (list, tuple)):
            return "\n".join(code)
        return code

    def getTaggedExecutionCodeLines(self):
        """
        tags:
            % - input variables
            $ - output variables
            # - self
        """
        inputNames = self.inputNames
        outputNames = self.outputNames

        if hasattr(self, "execute"):
            keywordParameters = ["{0} = %{0}%".format(inputNames[socket.identifier]) for socket in self.inputs]
            parameterString = ", ".join(keywordParameters)

            outputVariables = ["${}$".format(outputNames[socket.identifier]) for socket in self.outputs]
            outputString = ", ".join(outputVariables)

            executionString = outputString + " = #self#.execute(" + parameterString + ")"
            return [executionString]
        else:
            code = self.getExecutionCodeString()
            for inputName in inputNames:
                code = tagVariableName(code, inputName, "%")
            for outputName in outputNames:
                code = tagVariableName(code, outputName, "$")
            code = tagVariableName(code, "self", "#")
            return code.split("\n")

def tagVariableName(code, name, tag):
    """
    Find all occurences of 'name' in 'code' and set 'tag' before and after it.
    The occurence must not have a dot before it.
    """
    return re.sub(r"([^\.]|^)\b({})\b".format(name), r"\1{0}\2{0}".format(tag), code)

@persistent
def createMissingIdentifiers(scene = None):
    def unidentifiedNodes():
        for tree in getAnimationNodeTrees():
            for node in tree.nodes:
                if not issubclass(type(node), AnimationNode): continue
                if node.identifier == "": yield node

    for node in unidentifiedNodes():
        node.identifier = createIdentifier()

def createIdentifier():
    identifierLength = 15
    characters = "abcdefghijklmnopqrstuvwxyz" + "0123456789"
    return ''.join(random.choice(characters) for _ in range(identifierLength))



# Register
##################################

def registerHandlers():
    bpy.app.handlers.load_post.append(createMissingIdentifiers)

def unregisterHandlers():
    bpy.app.handlers.load_post.remove(createMissingIdentifiers)
