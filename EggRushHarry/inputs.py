"""Keyboard input, flattened into one small object per frame."""
import pygame


class Input:
    def __init__(self):
        self.left = self.right = self.up = self.down = 0
        self.jump_pressed = False      # edge: jump / confirm pressed this frame
        self.pause_pressed = False     # edge: Esc this frame
        self.quit_pressed = False      # edge: Q this frame

    def poll(self, events):
        keys = pygame.key.get_pressed()
        self.left = int(keys[pygame.K_LEFT] or keys[pygame.K_a])
        self.right = int(keys[pygame.K_RIGHT] or keys[pygame.K_d])
        self.up = int(keys[pygame.K_UP] or keys[pygame.K_w])
        self.down = int(keys[pygame.K_DOWN] or keys[pygame.K_s])
        self.jump_pressed = self.pause_pressed = self.quit_pressed = False
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z, pygame.K_LCTRL, pygame.K_RCTRL):
                    self.jump_pressed = True
                elif e.key == pygame.K_ESCAPE:
                    self.pause_pressed = True
                elif e.key == pygame.K_q:
                    self.quit_pressed = True
        return self
