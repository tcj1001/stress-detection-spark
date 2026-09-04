package com.stress.controller;

import com.stress.dto.ApiResponse;
import com.stress.dto.ChangePasswordRequest;
import com.stress.dto.LoginRequest;
import com.stress.dto.LoginResponse;
import com.stress.dto.RegisterRequest;
import com.stress.service.UserService;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UserService userService;

    public AuthController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping("/register")
    public ApiResponse<String> register(@Valid @RequestBody RegisterRequest req) {
        userService.register(req);
        return ApiResponse.success("注册成功");
    }

    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest req) {
        return ApiResponse.success(userService.login(req));
    }

    @PutMapping("/change-password")
    public ApiResponse<String> changePassword(@Valid @RequestBody ChangePasswordRequest req) {
        userService.changePassword(req);
        return ApiResponse.success("密码修改成功");
    }
}
