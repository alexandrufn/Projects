"""Keyboard and mouse input, flattened into one small object per frame."""
import pygame


class Input:
    def __init__(self):
        self.dx = self.dy = 0
        self.fire_l = self.fire_f = self.fire_r = False     # held: the three fixed gun.smoke-style shots
        self.mouse_fire = False                             # held: free aim towards the cursor
        self.mouse_pos = (0, 0)
        self.confirm = False          # edge: Space / Enter
        self.bomb = False             # edge: B / right mouse
        self.pause = False            # edge: Esc
        self.quit = False             # edge: Q
        self.mouse_active = False     # true once the mouse has been used

    def poll(self, events):
        keys = pygame.key.get_pressed()
        self.dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
        self.dy = int(keys[pygame.K_DOWN] or keys[pygame.K_s]) - int(keys[pygame.K_UP] or keys[pygame.K_w])
        self.fire_f = bool(keys[pygame.K_k] or keys[pygame.K_SPACE] or keys[pygame.K_x])
        self.fire_l = bool(keys[pygame.K_j] or keys[pygame.K_z])
        self.fire_r = bool(keys[pygame.K_l] or keys[pygame.K_c])
        buttons = pygame.mouse.get_pressed()
        self.mouse_pos = pygame.mouse.get_pos()
        self.mouse_fire = bool(buttons[0])
        self.confirm = self.bomb = self.pause = self.quit = False
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.confirm = True
                elif e.key in (pygame.K_b, pygame.K_e):
                    self.bomb = True
                elif e.key == pygame.K_ESCAPE:
                    self.pause = True
                elif e.key == pygame.K_q:
                    self.quit = True
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_active = True
                if e.button == 1:
                    self.confirm = True
                elif e.button == 3:
                    self.bomb = True
        return self
