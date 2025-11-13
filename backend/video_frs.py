import cv2
import face_recognition
import numpy as np
# This is a demo of running face recognition on a video file and saving the results to a new video file.
#
# PLEASE NOTE: This example requires OpenCV (the `cv2` library) to be installed only to read from your webcam.
# OpenCV is *not* required to use the face_recognition library. It's only required if you want to run this
# specific demo. If you have trouble installing it, try any of the other demos that don't require it instead.

# Open the input movie file
input_movie = cv2.VideoCapture("video3.mp4")
length = int(input_movie.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"Total frame count is {length}")
fps = int(input_movie.get(cv2.CAP_PROP_FPS))
print(f"Total frame count is {length}")
n_seconds = 0.3
frame_skip_interval = int(fps * n_seconds)
print(f"Frames to skip per {n_seconds} seconds: {frame_skip_interval}")
# Create an output movie file (make sure resolution/frame rate matches input video!)
#fourcc = cv2.VideoWriter_fourcc(*'XVID')
#output_movie = cv2.VideoWriter('output.avi', fourcc, 29.97, (640, 360))

# Load some sample pictures and learn how to recognize them.
lmm_image = face_recognition.load_image_file("lawrence-bishnoi-2.png")
print(f"Encoding face 1")
lmm_face_encoding = face_recognition.face_encodings(lmm_image)[0]
print(f"Encoded face 1... Encoding face 2")
al_image = face_recognition.load_image_file("person-2.png")
al_face_encoding = face_recognition.face_encodings(al_image)[0]
print(f"Encoded face 2")
known_faces = [
    lmm_face_encoding,
    al_face_encoding
]

# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
frame_number = 0

while input_movie.isOpened():
    # Grab a single frame of video
    ret, frame = input_movie.read()
    
    print(f"Processing frame {frame_number}")
    # Quit when the input video file ends
    if ret:
    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        if frame_number % frame_skip_interval == 0:
            print(f"Frame falls under our purview.... Processing")
            #rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Find all the faces and face encodings in the current frame of video
            print(f"Detecting Face locations in the current frame")
            face_locations = face_recognition.face_locations(rgb_frame)
            print(f"Detected Face locations in the current frame. Starting face encoding")
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            print(f"Finished face encoding in the current frame")
            print(f"Found {len(face_encodings)} in the current frame")
            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                print(f"Comparing faces in the current frame with known faces")
                match = face_recognition.compare_faces(known_faces, face_encoding, tolerance=0.50)
                print(match)
                # If you had more than 2 faces, you could make this logic a lot prettier
                # but I kept it simple for the demo
                name = None
                if match[0]:
                    name = "Lawrence Bishnoi"
                elif match[1]:
                    name = "Person 2"
                if name is not None:
                    face_names.append(f"{name} found in frame {frame_number}")
        frame_number += frame_skip_interval
        input_movie.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    else:
        input_movie.release()
        break
'''
    # Label the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        if not name:
            continue

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(frame, (left, bottom - 25), (right, bottom), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)

    # Write the resulting image to the output video file
    print("Writing frame {} / {}".format(frame_number, length))
    output_movie.write(frame)
'''
# All done!
#input_movie.release()
cv2.destroyAllWindows()

print(face_names)