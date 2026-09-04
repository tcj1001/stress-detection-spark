package com.stress.controller;

import com.stress.dto.ApiResponse;
import com.stress.dto.RegisterRequest;
import com.stress.entity.SysUser;
import com.stress.repository.UserRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.Map;

@RestController
@RequestMapping("/api/admin")
public class UserController {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public UserController(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @GetMapping("/users")
    public ApiResponse<Page<SysUser>> listUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword) {
        PageRequest pageRequest = PageRequest.of(page, size, Sort.by("id").descending());
        Page<SysUser> result;
        if (keyword != null && !keyword.trim().isEmpty()) {
            result = userRepository.findByUsernameContainingOrNicknameContaining(keyword.trim(), keyword.trim(), pageRequest);
        } else {
            result = userRepository.findAll(pageRequest);
        }
        return ApiResponse.success(result);
    }

    @PostMapping("/users")
    public ApiResponse<String> createUser(@Valid @RequestBody RegisterRequest req) {
        if (userRepository.existsByUsername(req.getUsername())) {
            return ApiResponse.error(400, "账号已存在");
        }
        SysUser user = new SysUser();
        user.setNickname(req.getNickname());
        user.setUsername(req.getUsername());
        user.setPassword(passwordEncoder.encode(req.getPassword()));
        userRepository.save(user);
        return ApiResponse.success("添加成功");
    }

    @PutMapping("/users/{id}/password")
    public ApiResponse<String> changePassword(@PathVariable Long id, @RequestBody Map<String, String> body) {
        String newPassword = body.get("newPassword");
        if (newPassword == null || newPassword.length() < 6) {
            return ApiResponse.error(400, "新密码至少6位");
        }
        SysUser user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("用户不存在"));
        user.setPassword(passwordEncoder.encode(newPassword));
        userRepository.save(user);
        return ApiResponse.success("密码修改成功");
    }

    @DeleteMapping("/users/{id}")
    public ApiResponse<String> deleteUser(@PathVariable Long id) {
        SysUser user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("用户不存在"));
        if ("ADMIN".equals(user.getRole())) {
            return ApiResponse.error(400, "不能删除管理员账号");
        }
        userRepository.deleteById(id);
        return ApiResponse.success("删除成功");
    }
}
