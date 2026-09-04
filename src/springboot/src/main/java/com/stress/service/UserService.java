package com.stress.service;

import com.stress.dto.ChangePasswordRequest;
import com.stress.dto.LoginRequest;
import com.stress.dto.LoginResponse;
import com.stress.dto.RegisterRequest;
import com.stress.entity.SysUser;
import com.stress.repository.UserRepository;
import com.stress.util.JwtUtil;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;
    private final String initialAdminPassword;

    public UserService(UserRepository userRepository, PasswordEncoder passwordEncoder, JwtUtil jwtUtil,
                       @Value("${app.admin.initial-password:}") String initialAdminPassword) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtUtil = jwtUtil;
        this.initialAdminPassword = initialAdminPassword;
    }

    @PostConstruct
    public void initAdmin() {
        SysUser admin = userRepository.findByUsername("admin").orElse(null);
        if (admin == null) {
            if (initialAdminPassword == null || initialAdminPassword.isBlank()) {
                return;
            }
            admin = new SysUser();
            admin.setUsername("admin");
            admin.setPassword(passwordEncoder.encode(initialAdminPassword));
        }
        admin.setNickname("管理员");
        admin.setRole("ADMIN");
        userRepository.save(admin);
    }

    public void register(RegisterRequest req) {
        if (userRepository.existsByUsername(req.getUsername())) {
            throw new RuntimeException("账号已存在");
        }
        SysUser user = new SysUser();
        user.setNickname(req.getNickname());
        user.setUsername(req.getUsername());
        user.setPassword(passwordEncoder.encode(req.getPassword()));
        userRepository.save(user);
    }

    public LoginResponse login(LoginRequest req) {
        SysUser user = userRepository.findByUsername(req.getUsername())
                .orElseThrow(() -> new RuntimeException("账号或密码错误"));
        if (!passwordEncoder.matches(req.getPassword(), user.getPassword())) {
            throw new RuntimeException("账号或密码错误");
        }
        String token = jwtUtil.generateToken(user.getUsername(), user.getRole());
        return new LoginResponse(token, user.getUsername(), user.getNickname(), user.getRole());
    }

    public void changePassword(ChangePasswordRequest req) {
        SysUser user = userRepository.findByUsername(req.getUsername())
                .orElseThrow(() -> new RuntimeException("账号不存在"));
        if (!passwordEncoder.matches(req.getOldPassword(), user.getPassword())) {
            throw new RuntimeException("原密码错误");
        }
        user.setPassword(passwordEncoder.encode(req.getNewPassword()));
        userRepository.save(user);
    }
}
