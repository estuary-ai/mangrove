# TODO
# class DataBuffer:
#     def __init__(self, frame_size=320):
#         self.queue = []
#         self.frame_size=frame_size

#     def __str__(self):
#         return ' '.join([str(i) for i in self.queue])

#     def isEmpty(self):
#         return len(self.queue) == 0
 
#     def insert(self, data):
#         timestamp, audio_bytes = data

#         for i, item in enumerate(self.queue):
#             self.queue.append()
 
#     # for popping an element based on Priority
#     def delete(self):
#         try:
#             max_val = 0
#             for i in range(len(self.queue)):
#                 if self.queue[i] > self.queue[max_val]:
#                     max_val = i
#             item = self.queue[max_val]
#             del self.queue[max_val]
#             return item
#         except IndexError:
#             print()
#             exit()
 
# if __name__ == '__main__':
#     myQueue = PriorityQueue()
#     myQueue.insert(12)
#     myQueue.insert(1)
#     myQueue.insert(14)
#     myQueue.insert(7)
#     print(myQueue)           
#     while not myQueue.isEmpty():
#         print(myQueue.delete())